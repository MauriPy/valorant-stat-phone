from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    secret: Mapped[str] = mapped_column(String(128), nullable=False)
    pairing_code: Mapped[str] = mapped_column(String(8), unique=True, nullable=False)
    firmware_version: Mapped[str | None] = mapped_column(String(32))
    linked_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime)

    user: Mapped["User | None"] = relationship(back_populates="device")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    riot_puuid: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    riot_game_name: Mapped[str] = mapped_column(String(64), nullable=False)
    riot_tag_line: Mapped[str] = mapped_column(String(16), nullable=False)
    access_token: Mapped[str | None] = mapped_column(Text)
    refresh_token: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str] = mapped_column(String(16), default="americas")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    device: Mapped[Device | None] = relationship(back_populates="user")

    @property
    def riot_id(self) -> str:
        return f"{self.riot_game_name}#{self.riot_tag_line}"


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

_db_url = settings.database_url
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(_db_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
