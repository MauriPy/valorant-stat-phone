"""Cliente Riot API + flujo RSO (OAuth2) para producto comercial."""

from __future__ import annotations

import secrets
from urllib.parse import urlencode

import httpx

from app.config import settings
from app.schemas import LastMatchStats


class RiotApiError(Exception):
    pass


class RiotRsoService:
    def __init__(self) -> None:
        self.client_id = settings.riot_client_id
        self.client_secret = settings.riot_client_secret
        self.redirect_uri = settings.riot_redirect_uri
        self.region = settings.riot_account_region

    def build_authorize_url(self, state: str) -> str:
        if not self.client_id:
            raise RiotApiError("RIOT_CLIENT_ID no configurado")

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid cpid offline_access",
            "state": state,
        }
        return f"{settings.riot_oauth_authorize_url}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        if not self.client_secret:
            raise RiotApiError("RIOT_CLIENT_SECRET no configurado")

        async with httpx.AsyncClient(timeout=30.0) as client:
            token_resp = await client.post(
                settings.riot_oauth_token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                },
                auth=(self.client_id, self.client_secret),
            )
            if token_resp.status_code >= 400:
                raise RiotApiError(f"Error OAuth Riot: {token_resp.text[:300]}")
            return token_resp.json()

    async def get_account_me(self, access_token: str) -> dict:
        url = f"https://{self.region}.api.riotgames.com/riot/account/v1/accounts/me"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {access_token}"})
            if resp.status_code >= 400:
                raise RiotApiError(f"No se pudo obtener cuenta Riot: {resp.text[:300]}")
            return resp.json()

    async def get_last_match(self, puuid: str, access_token: str) -> LastMatchStats:
        headers = {"Authorization": f"Bearer {access_token}"}
        base = f"https://{self.region}.api.riotgames.com"

        async with httpx.AsyncClient(timeout=30.0) as client:
            list_resp = await client.get(
                f"{base}/val/match/v1/matchlists/by-puuid/{puuid}",
                headers=headers,
            )
            if list_resp.status_code >= 400:
                raise RiotApiError(f"Error matchlist: {list_resp.text[:300]}")

            history = list_resp.json().get("history", [])
            if not history:
                raise RiotApiError("El jugador no tiene partidas recientes")

            match_id = history[0]["matchId"]
            match_resp = await client.get(
                f"{base}/val/match/v1/matches/{match_id}",
                headers=headers,
            )
            if match_resp.status_code >= 400:
                raise RiotApiError(f"Error match detail: {match_resp.text[:300]}")

            match = match_resp.json()

        player = next((p for p in match.get("players", []) if p.get("puuid") == puuid), None)
        if not player:
            raise RiotApiError("Jugador no encontrado en la partida")

        stats = player.get("stats", {})
        kills = int(stats.get("kills", 0))
        deaths = int(stats.get("deaths", 0))
        assists = int(stats.get("assists", 0))

        game_name = player.get("gameName", "")
        tag_line = player.get("tagLine", "")
        riot_id = f"{game_name}#{tag_line}" if game_name else puuid

        return LastMatchStats(
            riot_id=riot_id,
            kills=kills,
            deaths=deaths,
            assists=assists,
            kda_display=f"{kills}/{deaths}/{assists}",
            map_name=match.get("matchInfo", {}).get("mapId"),
            agent_name=player.get("characterId"),
            match_result=None,
            played_at=str(match.get("matchInfo", {}).get("gameStartMillis")),
            source="riot_api",
        )


def new_oauth_state() -> str:
    return secrets.token_urlsafe(24)
