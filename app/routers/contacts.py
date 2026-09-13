from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas, crud
from ..database import get_db

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


@router.post("", response_model=schemas.ContactOut)
def create_contact(payload: schemas.ContactCreate, db: Session = Depends(get_db)):
    customer = crud.get_or_create_customer(db, payload.phone, payload.name)
    contact = models.ContactMessage(
        customer_id=customer.id,
        name=payload.name,
        message=payload.message,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return schemas.ContactOut(
        id=contact.id,
        phone=customer.phone,
        name=contact.name,
        message=contact.message,
        created_at=contact.created_at,
    )
