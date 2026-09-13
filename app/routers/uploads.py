from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, crud
from ..database import get_db
from ..storage import upload_image

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE_BYTES = 8 * 1024 * 1024  # 8 MB


@router.post("", response_model=schemas.UploadedImageOut)
async def upload(
    file: UploadFile = File(...),
    phone: str | None = Form(None),
    name: str | None = Form(None),
    db: Session = Depends(get_db),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG or WEBP images are allowed")

    contents = await file.read()
    if len(contents) > MAX_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Image must be under 8MB")

    public_url, storage_path = upload_image(contents, file.filename, file.content_type)

    customer_id = None
    if phone:
        customer = crud.get_or_create_customer(db, phone, name)
        customer_id = customer.id

    image = models.UploadedImage(
        customer_id=customer_id,
        url=public_url,
        storage_path=storage_path,
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image
