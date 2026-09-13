from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/gallery", tags=["gallery"])


@router.get("", response_model=list[schemas.GalleryImageOut])
def list_gallery(category: str | None = None, db: Session = Depends(get_db)):
    query = db.query(models.GalleryImage)
    if category:
        query = query.filter(models.GalleryImage.category == category)
    return query.order_by(models.GalleryImage.created_at.desc()).all()
