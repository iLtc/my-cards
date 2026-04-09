from datetime import datetime
from pydantic import BaseModel, field_serializer


class CardCreate(BaseModel):
    name: str


class CardResponse(BaseModel):
    id: int
    name: str
    updated_at: datetime

    @field_serializer("updated_at")
    def serialize_updated_at(self, v: datetime) -> str:
        return v.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    model_config = {"from_attributes": True}
