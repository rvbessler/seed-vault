import os, json, base64, requests

TOKEN  = os.environ.get('GITHUB_TOKEN')
REPO   = os.environ.get('GITHUB_REPO')  # e.g. 'yourname/seed-vault'
PATH   = os.environ.get('VAULT_PATH', 'vault.json')
API    = f'https://api.github.com/repos/{REPO}/contents/{PATH}'
HEAD   = {
    'Authorization': f'token {TOKEN}',
    'Accept': 'application/vnd.github+json'
}

def _get():
    r = requests.get(API, headers=HEAD)
    if r.status_code == 200:
        meta = r.json()
        raw  = requests.get(meta['download_url']).text
        return json.loads(raw), meta['sha']
    if r.status_code == 404:
        return {}, None
    r.raise_for_status()

def load(engine_cls):
    data, sha = _get()
    eng = engine_cls.from_json(data) if data else engine_cls()
    return eng, sha

def save(vault_json: dict, sha: str | None):
    blob = base64.b64encode(
        json.dumps(vault_json, default=str).encode()
    ).decode()
    payload = {'message':'auto-save vault','content':blob,'sha':sha}
    r = requests.put(API, headers=HEAD, json=payload)
    r.raise_for_status()
    return r.json()['content']['sha']
