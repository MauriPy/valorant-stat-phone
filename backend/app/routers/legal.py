"""Paginas legales requeridas para productos comerciales (Riot, etc.)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import settings

router = APIRouter(tags=["legal"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/terms", response_class=HTMLResponse)
def terms_of_service(request: Request):
    return templates.TemplateResponse(
        "terms.html",
        {"request": request, "app_name": settings.app_name, "app_url": settings.app_url},
    )


@router.get("/privacy", response_class=HTMLResponse)
def privacy_policy(request: Request):
    return templates.TemplateResponse(
        "privacy.html",
        {"request": request, "app_name": settings.app_name, "app_url": settings.app_url},
    )
