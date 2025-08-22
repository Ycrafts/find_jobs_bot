import os
import requests
from typing import Dict, List, Tuple, Any

DEFAULT_HF_MODEL_ID = os.getenv('AI_MODEL_ID', 'facebook/bart-large-mnli')

# Broad domain labels for calibration (must include bot professions)
DOMAIN_LABELS: List[str] = [
    "Web Development",
    "Data Science",
    "UI/UX Design",
    "Mobile Development",
    "DevOps",
    "Product Management",
    "Content Writing",
    "Marketing",
    "Finance",
    "Human Resources",
    "Sales",
    "Accounting",
    "Customer Support",
    "Operations",
    "Project Management",
    "Education",
    "Healthcare",
    "Engineering",
    "Agriculture",
    "Legal",
    "Other",
]

# Simple in-memory cache for classification results
_ZSHOT_CACHE: Dict[Tuple[str, Tuple[str, ...], str, bool], Dict[str, float]] = {}
_MAX_CACHE_SIZE = 512


def _cache_set(cache: Dict, key, value):
    try:
        if len(cache) >= _MAX_CACHE_SIZE:
            cache.pop(next(iter(cache)))
        cache[key] = value
    except Exception:
        pass
    
class BaseAIMatcher:
    def score_job(self, user_profile: Dict[str, Any], job: Dict[str, Any]) -> float:
        raise NotImplementedError

    def score_jobs(self, user_profile: Dict[str, Any], jobs: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], float]]:
        scored: List[Tuple[Dict[str, Any], float]] = []
        for job in jobs:
            try:
                score = self.score_job(user_profile, job)
                scored.append((job, score))
            except Exception:
                # Skip jobs that fail to score
                continue
        # Sort descending by score
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored


def _build_profile_text(user_profile: Dict[str, Any]) -> str:
    location = user_profile.get('location') or {}
    loc_str = ''
    if isinstance(location, dict):
        lat = location.get('lat')
        lon = location.get('lon')
        if lat is not None and lon is not None:
            loc_str = f"Location: lat {lat}, lon {lon}."
    profession = user_profile.get('profession') or ''
    experience = user_profile.get('experience') or ''
    preferences = user_profile.get('preferences') or ''
    return (
        f"Profession: {profession}. Experience: {experience}. Preferences: {preferences}. {loc_str}"
    ).strip()


def _build_job_text(job: Dict[str, Any]) -> str:
    title = job.get('title') or ''
    company = job.get('company') or ''
    field = job.get('field') or ''
    experience = job.get('experience') or ''
    description = job.get('description') or ''
    return (
        f"Job title: {title}. Company: {company}. Field: {field}. "
        f"Experience: {experience}. Description: {description}"
    ).strip()


class HuggingFaceZeroShotMatcher(BaseAIMatcher):
    def __init__(self, api_key: str, model_id: str = DEFAULT_HF_MODEL_ID, timeout_seconds: int = 30):
        self.api_key = api_key
        self.model_id = model_id
        self.timeout_seconds = timeout_seconds
        self.endpoint = f"https://api-inference.huggingface.co/models/{self.model_id}"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _classify(self, text: str, labels: List[str], multi_label: bool) -> Dict[str, float]:
        # Cache lookup
        cache_key = (text, tuple(labels), self.model_id, multi_label)
        if cache_key in _ZSHOT_CACHE:
            return _ZSHOT_CACHE[cache_key]
        payload = {
            "inputs": text,
            "parameters": {
                "candidate_labels": labels,
                "hypothesis_template": "This text is about {}.",
                "multi_label": multi_label,
            },
            "options": {"wait_for_model": True},
        }
        try:
            resp = requests.post(self.endpoint, headers=self.headers, json=payload, timeout=self.timeout_seconds)
            if resp.status_code >= 400:
                return {}
            data = resp.json()
            if isinstance(data, list) and data:
                data = data[0]
            labels_out = data.get('labels') or []
            scores_out = data.get('scores') or []
            result = {lbl: float(scr) for lbl, scr in zip(labels_out, scores_out)}
            _cache_set(_ZSHOT_CACHE, cache_key, result)
            return result
        except Exception:
            return {}

    def _is_job_post(self, job_text: str) -> bool:
        try:
            scores = self._classify(job_text, ["Job Post", "Not a Job Post"], multi_label=False)
            return scores.get("Job Post", 0.0) >= 0.6
        except Exception:
            # If the classifier fails, do not block; consider it a job
            return True

    def _normalize_profession(self, profession: str) -> str:
        prof = (profession or '').strip()
        if not prof:
            return ''
        # Direct match if present
        if prof in DOMAIN_LABELS:
            return prof
        # Simple aliases
        alias_map = {
            "Software Engineering": "Engineering",
            "Software Engineer": "Engineering",
            "Backend Development": "Web Development",
            "Frontend Development": "Web Development",
            "Mobile": "Mobile Development",
            "Product": "Product Management",
            "HR": "Human Resources",
        }
        return alias_map.get(prof, prof)

    def score_job(self, user_profile: Dict[str, Any], job: Dict[str, Any]) -> float:
        job_text = _build_job_text(job)
        # Prefilter: drop obvious non-job posts (e.g., 'Test')
        if not self._is_job_post(job_text):
            return 0.0

        # If extractor provided a field and it matches the user's profession, trust it
        job_field = (job.get('field') or '').strip()
        user_profession = self._normalize_profession(user_profile.get('profession') or '')
        if job_field and user_profession and job_field.lower() == user_profession.lower():
            return 0.95

        # Otherwise, classify against a broad domain list and take the user's profession score
        labels = DOMAIN_LABELS
        scores = self._classify(job_text, labels, multi_label=True)
        if user_profession and user_profession in scores:
            return float(scores[user_profession])
        if job_field and job_field in scores:
            return float(scores[job_field])
        return float(scores.get('Other', 0.0))


def get_ai_matcher(config: Dict[str, Any]) -> BaseAIMatcher:
    provider = (config.get('AI_MATCH_PROVIDER') or 'huggingface_zeroshot').lower()
    if provider == 'huggingface_zeroshot':
        api_key = config.get('HF_API_KEY')
        if not api_key:
            raise ValueError("HF_API_KEY is required for Hugging Face zero-shot matcher")
        model_id = config.get('AI_MODEL_ID') or DEFAULT_HF_MODEL_ID
        return HuggingFaceZeroShotMatcher(api_key=api_key, model_id=model_id)
    raise ValueError(f"Unsupported AI_MATCH_PROVIDER: {provider}")


def select_top_matches(
    scored_jobs: List[Tuple[Dict[str, Any], float]],
    top_k: int = 5,
    min_score: float = 0.5,
) -> List[Tuple[Dict[str, Any], float]]:
    filtered = [(job, score) for job, score in scored_jobs if score >= min_score]
    return filtered[:top_k] 