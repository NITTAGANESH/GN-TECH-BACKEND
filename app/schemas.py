from datetime import datetime
from decimal import Decimal
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
    message: str = Field(..., min_length=1)


class ChatReplyCreate(BaseModel):
    message: str = Field(..., min_length=1)


class ChatMessageOut(BaseModel):
    id: int
    sender: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatConversationOut(BaseModel):
    phone: str
    name: str | None
    last_message: str
    last_sender: str
    last_message_at: datetime
    unread_count: int


class UploadedImageOut(BaseModel):
    id: int
    url: str
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionCreate(BaseModel):
    type: str = Field(..., pattern="^(income|expense)$")
    description: str = Field(..., min_length=1, max_length=255)
    amount: Decimal = Field(..., gt=0)


class TransactionOut(BaseModel):
    id: int
    type: str
    description: str
    amount: Decimal
    created_at: datetime

    class Config:
        from_attributes = True


class GalleryImageOut(BaseModel):
    id: int
    url: str
    title: str | None
    category: str
    created_at: datetime

    class Config:
        from_attributes = True


class BillItemIn(BaseModel):
    description: str = Field(..., min_length=1, max_length=255)
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)


class BillCreate(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=120)
    customer_phone: str = Field(..., min_length=6, max_length=20)
    items: list[BillItemIn] = Field(..., min_length=1)
    tax_percent: Decimal = Field(default=Decimal(0), ge=0, le=100)
    warranty: str | None = None
    notes: str | None = None


class BillOut(BaseModel):
    id: int
    bill_number: str
    customer_name: str
    customer_phone: str
    items: list[dict]
    subtotal: Decimal
    tax_percent: Decimal
    tax_amount: Decimal
    total: Decimal
    warranty: str | None
    notes: str | None
    pdf_url: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class AdminStats(BaseModel):
    total_customers: int
    total_contacts: int
    total_feedback: int
    average_rating: float
    total_chat_messages: int
    total_uploads: int
    total_income: Decimal
    total_expense: Decimal
    net_profit: Decimal
