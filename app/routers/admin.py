import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import require_admin
from ..database import get_db
from ..invoice_pdf import generate_invoice_pdf
from ..storage import upload_image, delete_image, upload_pdf

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


@router.get("/chats", response_model=list[schemas.ChatConversationOut])
def list_chats(db: Session = Depends(get_db)):
    customers_with_chat = (
        db.query(models.Customer)
        .join(models.ChatMessage, models.ChatMessage.customer_id == models.Customer.id)
        .distinct()
        .all()
    )

    conversations = []
    for customer in customers_with_chat:
        messages = (
            db.query(models.ChatMessage)
            .filter(models.ChatMessage.customer_id == customer.id)
            .order_by(models.ChatMessage.created_at.asc())
            .all()
        )
        if not messages:
            continue

        last = messages[-1]
        last_staff_at = next(
            (m.created_at for m in reversed(messages) if m.sender == "staff"), None
        )
        unread_count = sum(
            1
            for m in messages
            if m.sender == "customer" and (last_staff_at is None or m.created_at > last_staff_at)
        )

        conversations.append(
            schemas.ChatConversationOut(
                phone=customer.phone,
                name=customer.name,
                last_message=last.message,
                last_sender=last.sender,
                last_message_at=last.created_at,
                unread_count=unread_count,
            )
        )

    conversations.sort(key=lambda c: c.last_message_at, reverse=True)
    return conversations


@router.get("/chats/{phone}", response_model=list[schemas.ChatMessageOut])
def get_chat_thread(phone: str, db: Session = Depends(get_db)):
    customer = db.query(models.Customer).filter(models.Customer.phone == phone).first()
    if not customer:
        raise HTTPException(status_code=404, detail="No chat history for this number")

    return (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.customer_id == customer.id)
        .order_by(models.ChatMessage.created_at.asc())
        .all()
    )


@router.post("/chats/{phone}/reply", response_model=schemas.ChatMessageOut)
def reply_to_chat(phone: str, payload: schemas.ChatReplyCreate, db: Session = Depends(get_db)):
    customer = db.query(models.Customer).filter(models.Customer.phone == phone).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Unknown customer phone number")

    message = models.ChatMessage(
        customer_id=customer.id,
        sender="staff",
        message=payload.message,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@router.post("/bills", response_model=schemas.BillOut)
def create_bill(payload: schemas.BillCreate, db: Session = Depends(get_db)):
    items = []
    subtotal = Decimal(0)
    for item in payload.items:
        amount = item.quantity * item.unit_price
        subtotal += amount
        items.append(
            {
                "description": item.description,
                "quantity": float(item.quantity),
                "unit_price": float(item.unit_price),
                "amount": float(amount),
            }
        )

    tax_amount = (subtotal * payload.tax_percent / Decimal(100)).quantize(Decimal("0.01"))
    total = subtotal + tax_amount

    # Billing a phone number links it to the same customers table used by
    # contacts/feedback/chat/uploads, so a billed customer's history is all
    # tied together and they count toward admin stats - not just a name and
    # phone number sitting only on the bill itself.
    customer = crud.get_or_create_customer(db, payload.customer_phone, payload.customer_name)

    # bill_number is derived from the row's own database-assigned id once it
    # exists, which is the only value guaranteed to never collide - even
    # after older bills are deleted (unlike a row count or "max + 1", which
    # can repeat a number that's still in use elsewhere). A random
    # placeholder satisfies the NOT NULL/unique constraint for the brief
    # window before the real id is known.
    bill = models.Bill(
        bill_number=f"tmp{uuid.uuid4().hex[:12]}",
        customer_id=customer.id,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        items=items,
        subtotal=subtotal,
        tax_percent=payload.tax_percent,
        tax_amount=tax_amount,
        total=total,
        notes=payload.notes,
    )
    db.add(bill)
    db.commit()
    db.refresh(bill)

    bill.bill_number = f"GN-{bill.id:05d}"
    db.commit()
    db.refresh(bill)

    try:
        pdf_bytes = generate_invoice_pdf(bill)
        public_url, storage_path = upload_pdf(pdf_bytes, f"{bill.bill_number}.pdf")
        bill.pdf_url = public_url
        bill.storage_path = storage_path
        db.commit()
        db.refresh(bill)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Bill saved but PDF generation failed: {exc}")

    return bill


@router.get("/bills", response_model=list[schemas.BillOut])
def list_bills(db: Session = Depends(get_db)):
    return db.query(models.Bill).order_by(models.Bill.created_at.desc()).all()


@router.get("/bills/{bill_id}", response_model=schemas.BillOut)
def get_bill(bill_id: int, db: Session = Depends(get_db)):
    bill = db.query(models.Bill).filter(models.Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    return bill


@router.delete("/bills/{bill_id}")
def delete_bill(bill_id: int, db: Session = Depends(get_db)):
    bill = db.query(models.Bill).filter(models.Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    if bill.storage_path:
        delete_image(bill.storage_path)
    db.delete(bill)
    db.commit()
    return {"ok": True}
