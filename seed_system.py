"""
seed_system.py  –  v0.4a  –  2025-07-30
Self‑contained Seed System engine (ASCII only).
"""

from __future__ import annotations
import datetime as dt, random, textwrap, re
from functools import lru_cache
from typing import Dict, List, Optional

# Optional semantic layer
try:
    from sentence_transformers import SentenceTransformer, util
except ImportError:
    SentenceTransformer = None
    util = None

# ---------- helpers ----------
def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)

def kg_co2e(text: str) -> float:
    return round(len(text) * 2e-5, 4)

def fmt_carbon(c: float) -> str:
    return f"₡ {c:.4f} kg CO₂e"

def indent(txt: str, n:int=2) -> str:
    return textwrap.indent(txt, ' '*n)

# ---------- avoidance detector ----------
class AvoidanceDetector:
    patterns = [
        re.compile(r"\b(can(?:'t|not)|unable|no\s+way|impossible)\b", re.I),
        re.compile(r"\b(out\s+of\s+my\s+control|nothing\s+i\s+can\s+do)\b", re.I),
        re.compile(r"\b(inevitable|that's\s+just\s+how|always\s+been)\b", re.I),
        re.compile(r"\b(not\s+my\s+job|someone\s+else\s+should|they\s+need\s+to)\b", re.I),
        re.compile(r"\b(too\s+complex|too\s+complicated|over\s+my\s+head)\b", re.I),
    ]
    prototypes = [
        "I'm just one person",
        "Life isn't fair",
        "Nothing I do will matter",
        "It's out of my control",
        "Corporations won't change",
    ]
    threshold = 0.55
    _embedder=None; _proto_vecs=None

    @classmethod
    def _init_embedder(cls):
        if SentenceTransformer is None: return
        cls._embedder = SentenceTransformer("all-MiniLM-L6-v2")
        cls._proto_vecs = cls._embedder.encode(cls.prototypes, normalize_embeddings=True)

    @classmethod
    @lru_cache(maxsize=256)
    def detect(cls, text:str)->bool:
        if any(p.search(text) for p in cls.patterns):
            return True
        if SentenceTransformer is None:
            return False
        if cls._embedder is None:
            cls._init_embedder()
        q = cls._embedder.encode(text, normalize_embeddings=True)
        score = util.cos_sim(q, cls._proto_vecs).max().item()
        return score >= cls.threshold

# ---------- data classes ----------
class Seed:
    def __init__(self, seed_id:str, content:str, parent:str, planter:str, carbon:float):
        self.id, self.content, self.parent, self.planter, self.carbon = seed_id, content, parent, planter, carbon
        self.stamp = now()
        self.buried=False; self.burial_reason=None
    def fmt(self)->str:
        header=f"**{self.id}** (by {self.planter}, {self.stamp.date()})"
        return f"{header}\n{indent(self.content)}\n{fmt_carbon(self.carbon)}"
    def bury(self, reason:str): self.buried, self.burial_reason=True, reason

class SeedVault:
    def __init__(self, base_seed: Optional['Seed']=None):
        if base_seed is None:
            base_seed=Seed("SEED-0001","placeholder","ROOT","init",0.0)
        self.live={base_seed.id:base_seed}; self.buried={}; self.counter=1
    def new_seed(self, phrase:str,parent:str,planter:str)->'Seed':
        self.counter+=1
        sid=f"SEED-{self.counter:04d}"
        content=SeedGenerator.transform(phrase)
        seed=Seed(sid,content,parent,planter,kg_co2e(content))
        self.live[sid]=seed
        return seed
    def recent(self,n:int=5)->List['Seed']:
        return sorted(self.live.values(), key=lambda s:s.stamp, reverse=True)[:n]
    # JSON helpers
    def to_json(self):
        return {"live":{k:v.__dict__ for k,v in self.live.items()},
                "buried":{k:v.__dict__ for k,v in self.buried.items()},
                "counter":self.counter}
    @classmethod
    def from_json(cls,data):
        dummy=Seed("SEED-0000","x","ROOT","load",0.0)
        vault=cls(dummy)
        vault.live={k:Seed(**v) for k,v in data.get("live",{}).items()}
        vault.buried={k:Seed(**v) for k,v in data.get("buried",{}).items()}
        vault.counter=data.get("counter",1)
        return vault

class SeedGenerator:
    templates=["When you say '{p}' — what systems depend on that belief?",
               "'{p}' -> what suffering becomes invisible in this framing?",
               "Who profits if we accept '{p}' as inevitable?",
               "If '{p}' ended the conversation, what choice stays unopened?"]
    @classmethod
    def transform(cls,phrase:str)->str:
        return random.choice(cls.templates).format(p=phrase)

class TEECEngine:
    def __init__(self,user_alias:str="anon"):
        base_phrase="This is out of my control"
        base_seed=Seed("SEED-0001",SeedGenerator.transform(base_phrase),"ROOT",user_alias,kg_co2e(base_phrase))
        self.vault=SeedVault(base_seed)
        self.user_alias=user_alias
    def handle(self,msg:str)->str:
        if msg.startswith("/"):
            return self._cmd(msg)
        if AvoidanceDetector.detect(msg):
            return "Please consider using /seed \"{}\"".format(msg.strip())
        return "Let’s keep exploring—tell me more."
    def _cmd(self,cmd:str)->str:
        verb,*rest=cmd.split(maxsplit=1)
        if verb=="/seed":
            if not rest: return "Usage: /seed \"phrase\""
            phrase=rest[0].strip("\"'")
            seed=self.vault.new_seed(phrase,"SEED-0001",self.user_alias)
            return seed.fmt()
        if verb=="/seedcatalog":
            return "\n\n".join(s.fmt() for s in self.vault.recent(5)) or "No seeds"
        return f"Unknown command: {verb}"
