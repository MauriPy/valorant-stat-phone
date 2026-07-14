"""Cliente para Tracker Network API (uso comercial con clave de developers.tracker.gg)."""

from __future__ import annotations

import httpx

from app.config import settings
from app.schemas import LastMatchStats


class TrackerNetworkError(Exception):
    pass


class TrackerNetworkClient:
    def __init__(self) -> None:
        self.base_url = settings.tracker_api_base.rstrip("/")
        self.api_key = settings.tracker_api_key

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise TrackerNetworkError(
                "TRACKER_API_KEY no configurada. Solicita acceso en https://tracker.gg/developers"
            )
        return {
            "TRN-Api-Key": self.api_key,
            "Accept": "application/json",
            "User-Agent": f"{settings.app_name}/1.0",
        }

    async def get_last_match(self, riot_id: str) -> LastMatchStats:
        """
        Obtiene la ultima partida competitiva del jugador.

        Nota: ajusta rutas segun la documentacion oficial que te entregue Tracker Network
        al aprobar tu aplicacion comercial.
        """
        encoded_id = riot_id.replace("#", "%23")
        profile_url = f"{self.base_url}/v2/valorant/standard/profile/riot/{encoded_id}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            profile_resp = await client.get(profile_url, headers=self._headers())
            if profile_resp.status_code == 404:
                raise TrackerNetworkError(f"Perfil no encontrado: {riot_id}")
            if profile_resp.status_code >= 400:
                raise TrackerNetworkError(
                    f"Tracker API error {profile_resp.status_code}: {profile_resp.text[:200]}"
                )

            profile = profile_resp.json()
            matches = await self._fetch_recent_matches(client, encoded_id, profile)

        if not matches:
            raise TrackerNetworkError("No hay partidas recientes en el perfil")

        latest = matches[0]
        stats = self._extract_player_stats(latest, riot_id)
        return stats

    async def _fetch_recent_matches(
        self, client: httpx.AsyncClient, encoded_id: str, profile: dict
    ) -> list[dict]:
        """Intenta endpoint de matches; si falla, busca en segmentos del perfil."""
        matches_url = f"{self.base_url}/v2/valorant/standard/matches/riot/{encoded_id}"
        matches_resp = await client.get(
            matches_url,
            headers=self._headers(),
            params={"type": "match", "count": 1},
        )
        if matches_resp.status_code < 400:
            payload = matches_resp.json()
            if isinstance(payload, dict) and payload.get("data"):
                data = payload["data"]
                if isinstance(data, list):
                    return data
                if isinstance(data, dict) and data.get("matches"):
                    return data["matches"]

        segments = profile.get("data", {}).get("segments", profile.get("segments", []))
        match_segments = [
            s for s in segments if s.get("type") in ("match", "matchDetail", "match-detail")
        ]
        if match_segments:
            return sorted(match_segments, key=lambda s: s.get("metadata", {}).get("timestamp", 0), reverse=True)

        return []

    def _extract_player_stats(self, match: dict, riot_id: str) -> LastMatchStats:
        metadata = match.get("metadata", {})
        stats = match.get("stats", {}) or {}

        kills = int(stats.get("kills") or metadata.get("kills") or 0)
        deaths = int(stats.get("deaths") or metadata.get("deaths") or 0)
        assists = int(stats.get("assists") or metadata.get("assists") or 0)

        result = metadata.get("result") or stats.get("result")
        if isinstance(result, dict):
            result = result.get("outcome") or result.get("name")

        return LastMatchStats(
            riot_id=riot_id,
            kills=kills,
            deaths=deaths,
            assists=assists,
            kda_display=f"{kills}/{deaths}/{assists}",
            map_name=metadata.get("mapName") or metadata.get("map"),
            agent_name=metadata.get("agentName") or metadata.get("character"),
            match_result=str(result) if result else None,
            played_at=metadata.get("timestamp") or metadata.get("date"),
            source="tracker_network",
        )
