from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, crud
from ..database import get_db

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=schemas.ChatMessageOut)
def send_message(payload: schemas.ChatMessageCreate, db: Session = Depends(get_db)):
    customer = crud.get_or_create_customer(db, payload.phone, payload.name)
    message = models.ChatMessage(
        customer_id=customer.id,
        sender=payload.sender,
        message=payload.message,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@router.get("/{phone}", response_model=list[schemas.ChatMessageOut])
def get_history(phone: str, db: Session = Depends(get_db)):
    customer = db.query(models.Customer).filter(models.Customer.phone == phone).first()
    if not customer:
        raise HTTPException(status_code=404, detail="No chat history for this number")

    return (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.customer_id == customer.id)
        .order_by(models.ChatMessage.created_at.asc())
        .all()
    )
