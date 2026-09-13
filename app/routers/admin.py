from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import require_admin
from ..database import get_db
from ..storage import upload_image, delete_image

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.post("/login")
def login():
    # Reaching this endpoint at all means the X-Admin-Token header was valid
    # (checked by the router-level dependency above).
    return {"ok": True}


@router.get("/stats", response_model=schemas.AdminStats)
def get_stats(db: Session = Depends(get_db)):
    total_customers = db.query(func.count(models.Customer.id)).scalar() or 0
    total_contacts = db.query(func.count(models.ContactMessage.id)).scalar() or 0
    total_feedback = db.query(func.count(models.Feedback.id)).scalar() or 0
    average_rating = db.query(func.avg(models.Feedback.rating)).scalar() or 0
    total_chat_messages = db.query(func.count(models.ChatMessage.id)).scalar() or 0
    total_uploads = db.query(func.count(models.UploadedImage.id)).scalar() or 0

    total_income = (
        db.query(func.coalesce(func.sum(models.Transaction.amount), 0))
        .filter(models.Transaction.type == "income")
        .scalar()
    ) or Decimal(0)
    total_expense = (
        db.query(func.coalesce(func.sum(models.Transaction.amount), 0))
        .filter(models.Transaction.type == "expense")
        .scalar()
    ) or Decimal(0)

    return schemas.AdminStats(
        total_customers=total_customers,
        total_contacts=total_contacts,
        total_feedback=total_feedback,
        average_rating=round(float(average_rating), 2),
        total_chat_messages=total_chat_messages,
        total_uploads=total_uploads,
        total_income=total_income,
        total_expense=total_expense,
        net_profit=total_income - total_expense,
    )


@router.get("/feedback", response_model=list[schemas.FeedbackOut])
def list_feedback_admin(db: Session = Depends(get_db)):
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


@router.get("/contacts", response_model=list[schemas.ContactOut])
def list_contacts_admin(db: Session = Depends(get_db)):
    rows = (
        db.query(models.ContactMessage, models.Customer.phone)
        .join(models.Customer, models.ContactMessage.customer_id == models.Customer.id)
        .order_by(models.ContactMessage.created_at.desc())
        .all()
    )
    return [
        schemas.ContactOut(
            id=c.id,
            phone=phone,
            name=c.name,
            message=c.message,
            created_at=c.created_at,
        )
        for c, phone in rows
    ]


@router.post("/transactions", response_model=schemas.TransactionOut)
def create_transaction(payload: schemas.TransactionCreate, db: Session = Depends(get_db)):
    transaction = models.Transaction(
        type=payload.type,
        description=payload.description,
        amount=payload.amount,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("/transactions", response_model=list[schemas.TransactionOut])
def list_transactions(db: Session = Depends(get_db)):
    return (
        db.query(models.Transaction)
        .order_by(models.Transaction.created_at.desc())
        .all()
    )


@router.delete("/transactions/{transaction_id}")
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    transaction = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(transaction)
    db.commit()
    return {"ok": True}


ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE_BYTES = 8 * 1024 * 1024  # 8 MB


@router.post("/gallery", response_model=schemas.GalleryImageOut)
async def add_gallery_image(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    category: str = Form("gallery"),
    db: Session = Depends(get_db),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG or WEBP images are allowed")

    contents = await file.read()
    if len(contents) > MAX_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Image must be under 8MB")

    public_url, storage_path = upload_image(contents, file.filename, file.content_type)

    image = models.GalleryImage(
        url=public_url,
        storage_path=storage_path,
        title=title,
        category=category,
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


@router.get("/gallery", response_model=list[schemas.GalleryImageOut])
def list_gallery_admin(db: Session = Depends(get_db)):
    return db.query(models.GalleryImage).order_by(models.GalleryImage.created_at.desc()).all()


@router.delete("/gallery/{image_id}")
def delete_gallery_image(image_id: int, db: Session = Depends(get_db)):
    image = db.query(models.GalleryImage).filter(models.GalleryImage.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    delete_image(image.storage_path)
    db.delete(image)
    db.commit()
    return {"ok": True}
