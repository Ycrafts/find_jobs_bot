from supabase import create_client, Client

supabase: Client = None


class SupabaseRepository:
    def __init__(self, client: Client):
        self.client = client

    def save_user_profile(self, user_data):
        data = {
            'user_id': user_data['user_id'],
            'location': user_data['location'],
            'profession': user_data['profession'],
            'experience': user_data['experience'],
            'preferences': user_data['preferences'],
        }
        self.client.table('users').upsert(data).execute()

    def get_user_profile(self, user_id):
        result = self.client.table('users').select('*').eq('user_id', user_id).execute()
        return result.data[0] if result.data else None

    def save_job_post(self, job_data):
        url = job_data.get('url')
        if url:
            existing = self.client.table('jobs').select('id').eq('url', url).execute().data
            if existing:
                return
        self.client.table('jobs').upsert(job_data).execute()

    def get_matching_jobs(self, user_profile):
        profession = user_profile.get('profession', '')
        query = self.client.table('jobs').select('*')
        if profession:
            query = query.ilike('title', f'%{profession}%')
        return query.execute().data

    def get_new_matching_jobs(self, user_profile):
        profession = user_profile.get('profession', '')
        user_id = user_profile.get('user_id')
        query = self.client.table('jobs').select('*')
        if profession:
            query = query.ilike('title', f"%{profession}%")
        jobs = query.execute().data
        sent = self.client.table('sent_alerts').select('job_id').eq('user_id', user_id).execute().data
        sent_job_ids = {row['job_id'] for row in sent}
        return [job for job in jobs if job['id'] not in sent_job_ids]

    def mark_jobs_as_sent(self, user_id, jobs):
        rows = [{'user_id': user_id, 'job_id': job['id']} for job in jobs]
        if rows:
            self.client.table('sent_alerts').upsert(rows).execute()

    def fetch_all_users(self):
        return self.client.table('users').select('*').execute().data

    def fetch_unsent_jobs_for_user(self, user_id):
        jobs = self.client.table('jobs').select('*').order('id', desc=True).limit(200).execute().data
        sent = self.client.table('sent_alerts').select('job_id').eq('user_id', user_id).execute().data
        sent_job_ids = {row['job_id'] for row in sent}
        return [job for job in jobs if job['id'] not in sent_job_ids]


_repo: SupabaseRepository = None


def init_db(config):
    global supabase, _repo
    supabase = create_client(config['SUPABASE_URL'], config['SUPABASE_KEY'])
    _repo = SupabaseRepository(supabase)


def save_user_profile(user_data):
    if supabase is None:
        raise Exception("Supabase client not initialized. Call init_db(config) first.")
    if _repo is not None:
        return _repo.save_user_profile(user_data)


def get_user_profile(user_id):
    if supabase is None:
        raise Exception("Supabase client not initialized. Call init_db(config) first.")
    if _repo is not None:
        return _repo.get_user_profile(user_id)


def save_job_post(job_data):
    if supabase is None:
        raise Exception("Supabase client not initialized. Call init_db(config) first.")
    if _repo is not None:
        return _repo.save_job_post(job_data)


def get_matching_jobs(user_profile):
    if supabase is None:
        raise Exception("Supabase client not initialized. Call init_db(config) first.")
    if _repo is not None:
        return _repo.get_matching_jobs(user_profile)


def get_new_matching_jobs(user_profile):
    if supabase is None:
        raise Exception("Supabase client not initialized. Call init_db(config) first.")
    if _repo is not None:
        return _repo.get_new_matching_jobs(user_profile)


def mark_jobs_as_sent(user_id, jobs):
    if supabase is None:
        raise Exception("Supabase client not initialized. Call init_db(config) first.")
    if _repo is not None:
        return _repo.mark_jobs_as_sent(user_id, jobs)


def fetch_all_users():
    if supabase is None:
        raise Exception("Supabase client not initialized. Call init_db(config) first.")
    if _repo is not None:
        return _repo.fetch_all_users()


def fetch_unsent_jobs_for_user(user_id):
    if supabase is None:
        raise Exception("Supabase client not initialized. Call init_db(config) first.")
    if _repo is not None:
        return _repo.fetch_unsent_jobs_for_user(user_id) 