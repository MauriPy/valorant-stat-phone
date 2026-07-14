"""Endpoints que consume la ESP32."""

from __future__ import annotations

import secrets
import string
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Device, User, get_db
from app.schemas import DeviceRegisterRequest, DeviceRegisterResponse, DeviceStatsResponse
from app.services.riot_rso import RiotApiError
from app.services.henrik_dev import HenrikDevError
from app.services.stats import get_user_last_match
from app.services.tracker_network import TrackerNetworkError

router = APIRouter(prefix="/api/devices", tags=["devices"])


def _generate_pairing_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(6))


def _verify_device(device: Device | None, device_secret: str | None) -> Device:
    if device is None:
        raise HTTPException(status_code=404, detail="Dispositivo no registrado")
    if settings.require_device_secret and device_secret != device.secret:
        raise HTTPException(status_code=401, detail="Secreto de dispositivo invalido")
    return device


@router.post("/register", response_model=DeviceRegisterResponse)
def register_device(payload: DeviceRegisterRequest, db: Session = Depends(get_db)):
    """La ESP32 llama esto la primera vez (o tras reset de fabrica)."""
    device = db.get(Device, payload.device_id)
    if device is None:
        device = Device(
            id=payload.device_id,
            secret=secrets.token_urlsafe(32),
            pairing_code=_generate_pairing_code(),
            firmware_version=payload.firmware_version,
        )
        db.add(device)
    else:
        device.firmware_version = payload.firmware_version
        device.last_seen_at = datetime.utcnow()

    db.commit()
    db.refresh(device)

    setup_url = f"{settings.app_url.rstrip('/')}/setup?code={device.pairing_code}"
    return DeviceRegisterResponse(
        device_id=device.id,
        device_secret=device.secret,
        pairing_code=device.pairing_code,
        setup_url=setup_url,
    )


@router.get("/{device_id}/stats", response_model=DeviceStatsResponse)
async def device_stats(
    device_id: str,
    db: Session = Depends(get_db),
    x_device_secret: str | None = Header(default=None, alias="X-Device-Secret"),
):
    """
    La ESP32 hace polling aqui cada 2-5 minutos.
    Devuelve el KDA de la ultima partida del usuario vinculado.
    """
    device = _verify_device(db.get(Device, device_id), x_device_secret)
    device.last_seen_at = datetime.utcnow()
    db.commit()

    if device.linked_user_id is None:
        return DeviceStatsResponse(
            linked=False,
            message=f"Vincula tu cuenta en {settings.app_url}/setup?code={device.pairing_code}",
        )

    user = db.get(User, device.linked_user_id)
    if user is None:
        return DeviceStatsResponse(linked=False, message="Usuario vinculado no encontrado")

    try:
        last_match = await get_user_last_match(db, user)
    except (HenrikDevError, TrackerNetworkError, RiotApiError) as exc:
        # Mensaje corto: la ESP32 parsea JSON basico en el OLED
        short_msg = str(exc).split(":")[0][:40]
        return DeviceStatsResponse(
            linked=True,
            riot_id=user.riot_id,
            message=short_msg,
        )

    return DeviceStatsResponse(linked=True, riot_id=user.riot_id, last_match=last_match)
