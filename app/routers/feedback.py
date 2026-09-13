from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas, crud
from ..database import get_db

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post("", response_model=schemas.FeedbackOut)
def create_feedback(payload: schemas.FeedbackCreate, db: Session = Depends(get_db)):
    customer = crud.get_or_create_customer(db, payload.phone, payload.name)
    feedback = models.Feedback(
        customer_id=customer.id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return schemas.FeedbackOut(
        id=feedback.id,
        phone=customer.phone,
        rating=feedback.rating,
        comment=feedback.comment,
        created_at=feedback.created_at,
    )


@router.get("", response_model=list[schemas.FeedbackOut])
def list_feedback(db: Session = Depends(get_db)):
    rows = (
        db.query(models.Feedback, models.Customer.phone)
        .join(models.Customer, models.Feedback.customer_id == models.Customer.id)
        .order_by(models.Feedback.created_at.desc())
        .all()
    )
    return [
        schemas.FeedbackOut(
            id=fb.id,
            phone=phone,
            rating=fb.rating,
            comment=fb.comment,
            created_at=fb.created_at,
        )
        for fb, phone in rows
    ]
