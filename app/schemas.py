from datetime import datetime
from pydantic import BaseModel, Field


class ContactCreate(BaseModel):
    phone: str = Field(..., min_length=6, max_length=20)
    name: str | None = None
    message: str = Field(..., min_length=1)


class ContactOut(BaseModel):
    id: int
    phone: str
    name: str | None
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackCreate(BaseModel):
    phone: str = Field(..., min_length=6, max_length=20)
    name: str | None = None
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = None


class FeedbackOut(BaseModel):
    id: int
    phone: str
    rating: int
    comment: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    phone: str = Field(..., min_length=6, max_length=20)
    name: str | None = None
    sender: str = Field(..., pattern="^(customer|staff)$")
    message: str = Field(..., min_length=1)


class ChatMessageOut(BaseModel):
    id: int
    sender: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


class UploadedImageOut(BaseModel):
    id: int
    url: str
    created_at: datetime

    class Config:
        from_attributes = True
