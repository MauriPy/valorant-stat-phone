"""Flujo RSO: cada comprador inicia sesion con su cuenta Riot."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, URLSafeSerializer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Device, User, get_db
from app.schemas import DeviceLinkRequest
from app.services.riot_rso import RiotApiError, RiotRsoService, new_oauth_state

router = APIRouter(prefix="/auth", tags=["auth"])

serializer = URLSafeSerializer(settings.secret_key, salt="riot-oauth-state")
riot_service = RiotRsoService()


def _store_oauth_state(state: str, pairing_code: str | None) -> str:
    return serializer.dumps({"state": state, "pairing_code": pairing_code})


def _load_oauth_state(signed: str) -> dict:
    try:
        return serializer.loads(signed)
    except BadSignature as exc:
        raise HTTPException(status_code=400, detail="Estado OAuth invalido") from exc


@router.get("/riot/login")
async def riot_login(pairing_code: str | None = None):
    try:
        state = new_oauth_state()
        signed = _store_oauth_state(state, pairing_code)
        url = riot_service.build_authorize_url(signed)
    except RiotApiError as exc:
        setup_url = f"{settings.app_url.rstrip('/')}/setup"
        if pairing_code:
            setup_url += f"?code={pairing_code}&error={exc}"
        else:
            setup_url += f"?error={exc}"
        return RedirectResponse(setup_url, status_code=303)

    return RedirectResponse(url)


@router.get("/riot/callback")
async def riot_callback(code: str, state: str, db: Session = Depends(get_db)):
    payload = _load_oauth_state(state)
    pairing_code = payload.get("pairing_code")

    try:
        tokens = await riot_service.exchange_code(code)
        account = await riot_service.get_account_me(tokens["access_token"])
    except RiotApiError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    puuid = account["puuid"]
    game_name = account["gameName"]
    tag_line = account["tagLine"]

    user = db.query(User).filter(User.riot_puuid == puuid).one_or_none()
    if user is None:
        user = User(
            riot_puuid=puuid,
            riot_game_name=game_name,
            riot_tag_line=tag_line,
            access_token=tokens.get("access_token"),
            refresh_token=tokens.get("refresh_token"),
        )
        db.add(user)
    else:
        user.riot_game_name = game_name
        user.riot_tag_line = tag_line
        user.access_token = tokens.get("access_token")
        user.refresh_token = tokens.get("refresh_token")

    db.flush()

    if pairing_code:
        device = db.query(Device).filter(Device.pairing_code == pairing_code.upper()).one_or_none()
        if device:
            device.linked_user_id = user.id
            device.pairing_code = device.pairing_code  # mantiene codigo por si hay que re-vincular

    db.commit()

    return RedirectResponse(f"{settings.app_url.rstrip('/')}/setup/success?riot_id={game_name}%23{tag_line}")


@router.post("/link-device")
def link_device_with_riot_session(
    payload: DeviceLinkRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Alternativa si el login Riot ya ocurrio en otra pestana.
    En produccion, protege este endpoint con sesion de usuario.
    """
    device = db.query(Device).filter(Device.pairing_code == payload.pairing_code.upper()).one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail="Codigo de emparejamiento invalido")
    return {"device_id": device.id, "linked": device.linked_user_id is not None}
