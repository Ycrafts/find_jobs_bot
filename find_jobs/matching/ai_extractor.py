import os
from typing import Dict, Any, Optional, List, Tuple
import requests


DEFAULT_FIELD_LABELS: List[str] = [
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

EXPERIENCE_LABELS: List[str] = [
    "Entry Level",
    "Mid Level",
    "Senior Level",
    "Lead/Manager",
]

# Simple in-memory caches to limit repeated API calls per identical input
_ZSHOT_CACHE: Dict[Tuple[str, Tuple[str, ...], str, bool], List[Tuple[str, float]]] = {}
_NER_CACHE: Dict[Tuple[str, str], Dict[str, Any]] = {}
_MAX_CACHE_SIZE = 512


def _cache_set(cache: Dict, key, value):
    try:
        if len(cache) >= _MAX_CACHE_SIZE:
            # Drop one arbitrary item (simple cap)
            cache.pop(next(iter(cache)))
        cache[key] = value
    except Exception:
        pass


class _HFZeroShot:
    def __init__(self, api_key: str, model_id: str):
        self.api_key = api_key
        self.model_id = model_id or os.getenv('AI_MODEL_ID', 'facebook/bart-large-mnli')
        self.endpoint = f"https://api-inference.huggingface.co/models/{self.model_id}"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def classify(self, text: str, labels: List[str], multi_label: bool = False) -> List[Tuple[str, float]]:
        if not text or not labels:
            return []
        # Cache lookup
        key = (text, tuple(labels), self.model_id, multi_label)
        if key in _ZSHOT_CACHE:
            return _ZSHOT_CACHE[key]
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
            resp = requests.post(self.endpoint, headers=self.headers, json=payload, timeout=30)
            # If rate-limited or server error, return empty gracefully
            if resp.status_code >= 400:
                return []
            data = resp.json()
            if isinstance(data, list) and data:
                data = data[0]
            labels_out = data.get('labels') or []
            scores_out = data.get('scores') or []
            result = list(zip(labels_out, scores_out))
            _cache_set(_ZSHOT_CACHE, key, result)
            return result
        except Exception:
            return []


class _HFNERAPI:
    def __init__(self, api_key: str, model_id: Optional[str] = None):
        self.api_key = api_key
        self.model_id = model_id or os.getenv('AI_NER_MODEL_ID', 'dslim/bert-base-NER')
        self.endpoint = f"https://api-inference.huggingface.co/models/{self.model_id}"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def extract(self, text: str) -> Dict[str, Any]:
        if not text:
            return {}
        # Cache lookup
        key = (text, self.model_id)
        if key in _NER_CACHE:
            return _NER_CACHE[key]
        payload = {
            "inputs": text,
            "parameters": {
                "aggregation_strategy": "simple",
            },
            "options": {"wait_for_model": True},
        }
        try:
            resp = requests.post(self.endpoint, headers=self.headers, json=payload, timeout=30)
            if resp.status_code >= 400:
                return {}
            data = resp.json()
            if isinstance(data, list) and len(data) == 1 and isinstance(data[0], list):
                entities = data[0]
            elif isinstance(data, list):
                entities = data
            else:
                entities = []
            company = None
            location = None
            for ent in entities:
                label = ent.get('entity_group') or ent.get('entity')
                value = ent.get('word') or ent.get('entity')
                if not value or not label:
                    continue
                if company is None and label in ("ORG", "MISC"):
                    company = value.strip()
                if location is None and label in ("LOC", "GPE"):
                    location = value.strip()
                if company and location:
                    break
            out: Dict[str, Any] = {}
            if company:
                out['company'] = company
            if location:
                out['location'] = location
            _cache_set(_NER_CACHE, key, out)
            return out
        except Exception:
            return {}


def _normalize_experience(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    text = raw.strip().lower()
    if any(k in text for k in ["entry", "junior", "fresh"]):
        return "Entry Level"
    if any(k in text for k in ["mid", "intermediate"]):
        return "Mid Level"
    if any(k in text for k in ["senior", "sr", "5+ years", "5 years", "6 years", "7 years", "8 years"]):
        return "Senior Level"
    if any(k in text for k in ["lead", "manager", "head", "principal", "director"]):
        return "Lead/Manager"
    return None


def extract_fields(text: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    AI-based extraction of company, location, field, and experience from free text.
    Uses HF zero-shot (API) for field/experience and HF Inference API NER for company/location.
    Returns only fields it can infer with reasonable confidence; otherwise omits them.
    """
    results: Dict[str, Any] = {}
    if not text or len(text.strip()) < 15:
        return results

    api_key = (config.get('HF_API_KEY') or '').strip()
    model_id = (config.get('AI_MODEL_ID') or '').strip() or 'facebook/bart-large-mnli'

    # Field and experience via zero-shot
    try:
        if api_key:
            zshot = _HFZeroShot(api_key=api_key, model_id=model_id)
            field_scores = zshot.classify(text, DEFAULT_FIELD_LABELS, multi_label=True)
            if field_scores:
                field_scores.sort(key=lambda x: x[1], reverse=True)
                top_field, top_field_score = field_scores[0]
                if top_field_score >= 0.5 and top_field != "Other":
                    results['field'] = top_field
            exp_scores = zshot.classify(text, EXPERIENCE_LABELS, multi_label=False)
            if exp_scores:
                exp_scores.sort(key=lambda x: x[1], reverse=True)
                top_exp, top_exp_score = exp_scores[0]
                if top_exp_score >= 0.4:
                    results['experience'] = top_exp
    except Exception:
        pass

    # Company and location via HF NER API (best effort)
    try:
        if api_key:
            ner = _HFNERAPI(api_key=api_key)
            ner_out = ner.extract(text)
            for k in ('company', 'location'):
                if k in ner_out:
                    results[k] = ner_out[k]
    except Exception:
        pass

    # Heuristic normalization fallback for experience
    if 'experience' not in results:
        normalized = _normalize_experience(text)
        if normalized:
            results['experience'] = normalized

    return results 