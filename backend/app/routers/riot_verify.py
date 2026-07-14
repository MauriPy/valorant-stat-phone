"""Verificacion de dominio para Riot Developer Portal (GET /riot.txt)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.config import settings

router = APIRouter(tags=["riot"])

_RIOT_TXT_PATH = Path(__file__).resolve().parent.parent.parent / "riot.txt"


def _verification_code() -> str:
    if settings.riot_verification_code.strip():
        return settings.riot_verification_code.strip()
    if _RIOT_TXT_PATH.exists():
        return _RIOT_TXT_PATH.read_text(encoding="utf-8").strip()
    return ""


@router.get("/riot.txt", response_class=PlainTextResponse)
def riot_verification_file():
    return PlainTextResponse(content=_verification_code(), media_type="text/plain")
