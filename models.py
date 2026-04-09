from datetime import datetime, timezone
from sqlalchemy import String, DateTime, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Card(Base):
    __tablename__ = "card"
    __table_args__ = (UniqueConstraint("name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
