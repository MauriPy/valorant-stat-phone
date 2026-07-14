"""Cliente HenrikDev API — alternativa gratuita para desarrollo (Valorant)."""

from __future__ import annotations

from urllib.parse import quote

import httpx

from app.config import settings
from app.schemas import LastMatchStats

HENRIK_BASE = "https://api.henrikdev.xyz"
REGIONS = ("latam", "na", "br", "eu", "ap", "kr")


class HenrikDevError(Exception):
    pass


class HenrikDevClient:
    def __init__(self) -> None:
        self.api_key = settings.henrik_api_key

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise HenrikDevError(
                "HENRIK_API_KEY no configurada. Obten una gratis en https://api.henrikdev.xyz/dashboard/"
            )
        return {"Authorization": self.api_key, "Accept": "application/json"}

    def _params(self) -> dict[str, str]:
        return {"api_key": self.api_key} if self.api_key else {}

    async def get_last_match(self, riot_id: str) -> LastMatchStats:
        if "#" not in riot_id:
            raise HenrikDevError("Riot ID invalido. Formato: Nombre#TAG")

        game_name, tag_line = riot_id.split("#", 1)
        game_name = game_name.strip()
        tag_line = tag_line.strip()

        async with httpx.AsyncClient(timeout=30.0) as client:
            last_error = "Sin partidas recientes"
            for region in REGIONS:
                encoded_name = quote(game_name)
                url = f"{HENRIK_BASE}/valorant/v4/matches/{region}/pc/{encoded_name}/{tag_line}"
                resp = await client.get(url, headers=self._headers(), params={**self._params(), "size": 1})
                if resp.status_code == 404:
                    continue
                if resp.status_code == 401:
                    raise HenrikDevError("HenrikDev API key invalida o expirada")
                if resp.status_code >= 400:
                    last_error = f"HenrikDev {resp.status_code}: {resp.text[:120]}"
                    continue

                payload = resp.json()
                matches = payload.get("data") or []
                if not matches:
                    continue

                return self._extract_stats(matches[0], riot_id, region)

        raise HenrikDevError(last_error)

    def _extract_stats(self, match: dict, riot_id: str, region: str) -> LastMatchStats:
        metadata = match.get("metadata", {})
        map_meta = metadata.get("map")
        map_name = map_meta.get("name") if isinstance(map_meta, dict) else map_meta

        players = match.get("players", [])
        if isinstance(players, dict):
            players = list(players.values())
        if not players:
            players = match.get("stats", {}).get("all_players", [])

        player = None
        game_name, tag_line = riot_id.split("#", 1)
        for p in players:
            name = p.get("name") or p.get("gameName") or ""
            tag = p.get("tag") or p.get("tagLine") or ""
            if name.lower() == game_name.strip().lower() and tag.lower() == tag_line.strip().lower():
                player = p
                break

        if player is None and players:
            player = players[0]

        if player is None:
            raise HenrikDevError("Jugador no encontrado en la partida")

        stats = player.get("stats", player)
        kills = int(stats.get("kills", 0))
        deaths = int(stats.get("deaths", 0))
        assists = int(stats.get("assists", 0))

        agent = player.get("agent")
        agent_name = agent.get("name") if isinstance(agent, dict) else player.get("character")

        return LastMatchStats(
            riot_id=riot_id,
            kills=kills,
            deaths=deaths,
            assists=assists,
            kda_display=f"{kills}/{deaths}/{assists}",
            map_name=map_name,
            agent_name=agent_name,
            match_result=stats.get("result") or player.get("team"),
            played_at=str(metadata.get("game_start_patched") or metadata.get("game_start")),
            source=f"henrik_dev:{region}",
        )
