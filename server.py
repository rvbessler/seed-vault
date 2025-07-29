import os, uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from seed_system import TEECEngine
import persistence

app = FastAPI(title='Seed System API')
sessions = {}  # session_id -> (engine, sha)

class SeedReq(BaseModel):
    session_id: str
    user_msg: str

class SeedResp(BaseModel):
    assistant_msg: str

@app.post('/seed_handle', response_model=SeedResp)
def seed_handle(req: SeedReq):
    eng, sha = sessions.get(req.session_id, (None, None))
    if eng is None:
        eng, sha = persistence.load(TEECEngine)
    reply = eng.handle(req.user_msg)
    sha = persistence.save(eng.vault.to_json(), sha)
    sessions[req.session_id] = (eng, sha)
    return {'assistant_msg': reply}

@app.get('/ping')
def ping():
    return {'status':'ok'}

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=int(os.getenv('PORT', 8000)))
