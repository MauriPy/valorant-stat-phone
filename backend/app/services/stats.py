"""Orquestador: elige proveedor de stats segun configuracion."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import settings
from app.database import User
from app.schemas import LastMatchStats
from app.services.riot_rso import RiotApiError, RiotRsoService
from app.services.tracker_network import TrackerNetworkClient, TrackerNetworkError


class StatsService:
    def __init__(self) -> None:
        self.tracker = TrackerNetworkClient()
        self.riot = RiotRsoService()

    async def get_last_match_for_user(self, user: User) -> LastMatchStats:
        if settings.stats_provider == "riot":
            if not user.access_token:
                raise RiotApiError("Usuario sin token Riot. Repite el login RSO.")
            return await self.riot.get_last_match(user.riot_puuid, user.access_token)

        return await self.tracker.get_last_match(user.riot_id)


async def get_user_last_match(db: Session, user: User) -> LastMatchStats:
    service = StatsService()
    try:
        return await service.get_last_match_for_user(user)
    except (TrackerNetworkError, RiotApiError):
        raise
