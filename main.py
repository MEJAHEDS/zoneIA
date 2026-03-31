"""
ZoneAI — FastAPI server
Mini Map Analytix powered by Claude AI Agent
"""
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from agent import analyze_location
from limiter import check_and_increment, get_real_ip

app = FastAPI(title="ZoneAI", description="Analyse de zone de chalandise par IA", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ────────────────────────────────────────────────────────────────────

class AnalysisRequest(BaseModel):
    address: str
    business_type: str = "restaurant"


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    html = Path("index.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html)


@app.post("/analyze")
async def analyze(req: AnalysisRequest, request: Request):
    """
    Main endpoint: run Claude agent to analyze a location.
    Rate limited: 2 requests per IP per 24h.
    """
    if not req.address.strip():
        raise HTTPException(status_code=400, detail="L'adresse ne peut pas être vide.")
    if not req.business_type.strip():
        raise HTTPException(status_code=400, detail="Le type d'établissement ne peut pas être vide.")

    # ── Rate limiting ──────────────────────────────────────────────────────────
    ip = get_real_ip(request)
    limit = check_and_increment(ip)

    if not limit["allowed"]:
        hours = limit["reset_in"] // 3600
        minutes = (limit["reset_in"] % 3600) // 60
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": str(limit["reset_in"])},
            content={
                "error": "rate_limited",
                "message": f"Limite atteinte (2 analyses / 24h). Réessayez dans {hours}h {minutes}min.",
                "reset_in_seconds": limit["reset_in"],
            },
        )

    result = await analyze_location(req.address, req.business_type)
    result["remaining_requests"] = limit["remaining"]
    return result


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ZoneAI"}
