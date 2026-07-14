"""Paginas web para que el comprador vincule su dispositivo."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Device, User, get_db

router = APIRouter(tags=["setup"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/setup", response_class=HTMLResponse)
def setup_page(
    request: Request,
    code: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    device = None
    if code:
        device = db.query(Device).filter(Device.pairing_code == code.upper()).one_or_none()

    login_url = f"/auth/riot/login?pairing_code={code}" if code else "/auth/riot/login"
    riot_oauth_ready = bool(settings.riot_client_id and settings.riot_client_secret)
    return templates.TemplateResponse(
        "setup.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "pairing_code": code,
            "device": device,
            "login_url": login_url,
            "stats_provider": settings.stats_provider,
            "dev_manual_link": settings.dev_allow_manual_link,
            "riot_oauth_ready": riot_oauth_ready,
            "error": error,
        },
    )


@router.post("/setup/link-manual")
def link_manual(
    pairing_code: str = Form(...),
    riot_id: str = Form(...),
    db: Session = Depends(get_db),
):
    """Desarrollo: vincular Poison#YEAH sin RSO mientras no tengas clave Riot."""
    if not settings.dev_allow_manual_link:
        raise HTTPException(status_code=403, detail="Vinculacion manual desactivada")

    if "#" not in riot_id:
        raise HTTPException(status_code=400, detail="Formato: Nombre#TAG")

    game_name, tag_line = riot_id.split("#", 1)
    device = db.query(Device).filter(Device.pairing_code == pairing_code.upper()).one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail="Codigo invalido")

    puuid = f"manual-{game_name}-{tag_line}".lower()
    user = db.query(User).filter(User.riot_puuid == puuid).one_or_none()
    if user is None:
        user = User(riot_puuid=puuid, riot_game_name=game_name, riot_tag_line=tag_line)
        db.add(user)
    else:
        user.riot_game_name = game_name
        user.riot_tag_line = tag_line

    db.flush()
    device.linked_user_id = user.id
    db.commit()

    encoded = riot_id.replace("#", "%23")
    return RedirectResponse(f"/setup/success?riot_id={encoded}", status_code=303)


@router.get("/setup/success", response_class=HTMLResponse)
def setup_success(request: Request, riot_id: str | None = None):
    return templates.TemplateResponse(
        "success.html",
        {"request": request, "app_name": settings.app_name, "riot_id": riot_id},
    )
