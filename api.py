import os

from fastapi import FastAPI, Header, HTTPException

from storage import get_by_date, get_latest, init_db

app = FastAPI()
API_SECRET = os.environ.get("BRIEFING_API_SECRET", "")


def check_auth(authorization: str = Header("")):
    if not API_SECRET:
        raise HTTPException(503, "API not configured")
    if authorization != f"Bearer {API_SECRET}":
        raise HTTPException(401, "Unauthorized")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/briefing/latest")
def latest(authorization: str = Header("")):
    check_auth(authorization)
    briefing = get_latest()
    if not briefing:
        raise HTTPException(404, "No briefings yet")
    return briefing


@app.get("/api/briefing/{date}")
def by_date(date: str, authorization: str = Header("")):
    check_auth(authorization)
    briefing = get_by_date(date)
    if not briefing:
        raise HTTPException(404, "Not found")
    return briefing


@app.get("/health")
def health():
    return {"status": "ok"}
