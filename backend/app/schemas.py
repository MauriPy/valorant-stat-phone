from pydantic import BaseModel, Field


class DeviceRegisterRequest(BaseModel):
    device_id: str = Field(min_length=8, max_length=64)
    firmware_version: str | None = None


class DeviceRegisterResponse(BaseModel):
    device_id: str
    device_secret: str
    pairing_code: str
    setup_url: str


class LastMatchStats(BaseModel):
    riot_id: str
    kills: int
    deaths: int
    assists: int
    kda_display: str
    map_name: str | None = None
    agent_name: str | None = None
    match_result: str | None = None
    played_at: str | None = None
    source: str


class DeviceStatsResponse(BaseModel):
    linked: bool
    riot_id: str | None = None
    last_match: LastMatchStats | None = None
    message: str | None = None


class DeviceLinkRequest(BaseModel):
    pairing_code: str = Field(min_length=6, max_length=8)


class HealthResponse(BaseModel):
    status: str
    app: str
    stats_provider: str
