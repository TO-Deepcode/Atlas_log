from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
import sqlite3, os
from dotenv import load_dotenv

load_dotenv()
DB_PATH = "atlas.db"
API_KEY = os.getenv("ATLAS_KEY", "change-me")

app = FastAPI(title="Atlas Log API", version="1.0")

def db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS plan(
        id INTEGER PRIMARY KEY, ts INTEGER, symbol TEXT, timeframe TEXT,
        zone TEXT, invalidation TEXT, tps TEXT, status TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS exec(
        id INTEGER PRIMARY KEY, ts INTEGER, symbol TEXT, entry REAL, sl REAL, rr REAL, notes TEXT)""")
    return con

class Plan(BaseModel):
    symbol: str
    timeframe: str
    zone: str
    invalidation: str
    tps: list[str] = []
    status: str = "active"

class Exec(BaseModel):
    symbol: str
    entry: float
    sl: float
    rr: float
    notes: str = ""

def auth(key):
    if key != API_KEY:
        raise HTTPException(401, "bad key")

@app.post("/v1/plan")
def create_plan(p: Plan, x_atlas_key: str = Header(None)):
    auth(x_atlas_key)
    con = db()
    con.execute("INSERT INTO plan(ts,symbol,timeframe,zone,invalidation,tps,status) VALUES(?,?,?,?,?,?,?)",
                (int(datetime.utcnow().timestamp()), p.symbol, p.timeframe, p.zone, p.invalidation, "|".join(p.tps), p.status))
    con.commit()
    con.close()
    return {"ok": True}

@app.post("/v1/execution")
def add_exec(e: Exec, x_atlas_key: str = Header(None)):
    auth(x_atlas_key)
    con = db()
    con.execute("INSERT INTO exec(ts,symbol,entry,sl,rr,notes) VALUES(?,?,?,?,?,?)",
                (int(datetime.utcnow().timestamp()), e.symbol, e.entry, e.sl, e.rr, e.notes))
    con.commit()
    con.close()
    return {"ok": True}

@app.get("/v1/performance")
def performance(days: int = 30, x_atlas_key: str = Header(None)):
    auth(x_atlas_key)
    con = db()
    since = int((datetime.utcnow() - timedelta(days=days)).timestamp())
    rows = con.execute("SELECT rr FROM exec WHERE ts>=?", (since,)).fetchall()
    rrs = [r[0] for r in rows]
    n = len(rrs)
    hit = sum(1 for x in rrs if x > 0)
    hit_rate = (hit / n * 100) if n else 0.0
    avg_rr = (sum(rrs)/n) if n else 0.0
    net_r = sum(rrs)
    con.close()
    return {"count": n, "hit_rate": hit_rate, "avg_rr": avg_rr, "net_r": net_r}
