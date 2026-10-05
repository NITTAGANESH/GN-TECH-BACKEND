from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models
from ..auth import require_admin
from ..database import get_db

router = APIRouter(prefix="/api/reviews", tags=["reviews"])
admin_router = APIRouter(
    prefix="/api/admin/reviews", tags=["admin"], dependencies=[Depends(require_admin)]
)

SUMMARY_KEYS = ("rating", "total", "maps_url", "write_url")


class SummaryIn(BaseModel):
    rating: float | None = Field(default=None, ge=0, le=5)
    total: int | None = Field(default=None, ge=0)
    maps_url: str | None = None
    write_url: str | None = None


class ReviewIn(BaseModel):
    author: str = Field(..., min_length=1, max_length=120)
    rating: int = Field(..., ge=1, le=5)
    text: str | None = None
    when: str | None = Field(default=None, max_length=60)


def _get_setting(db: Session, key: str) -> str | None:
    row = db.query(models.SiteSetting).filter(models.SiteSetting.key == f"reviews_{key}").first()
    return row.value if row and row.value not in (None, "") else None


def _payload(db: Session) -> dict:
    rating = _get_setting(db, "rating")
    total = _get_setting(db, "total")
    items = db.query(models.ReviewItem).order_by(models.ReviewItem.id.desc()).all()
    return {
        "configured": bool(rating or total or items),
        "rating": float(rating) if rating else None,
        "total": int(total) if total else None,
        "maps_url": _get_setting(db, "maps_url"),
        "write_url": _get_setting(db, "write_url"),
        "reviews": [
            {"id": r.id, "author": r.author, "rating": r.rating, "text": r.text or "", "when": r.when_text or ""}
            for r in items
        ],
    }


@router.get("")
def get_reviews(db: Session = Depends(get_db)):
    return _payload(db)


@admin_router.get("")
def admin_get_reviews(db: Session = Depends(get_db)):
    return _payload(db)


@admin_router.put("/summary")
def save_summary(payload: SummaryIn, db: Session = Depends(get_db)):
    for key in SUMMARY_KEYS:
        value = getattr(payload, key)
        row = db.query(models.SiteSetting).filter(models.SiteSetting.key == f"reviews_{key}").first()
        value = "" if value is None else str(value).strip()
        if row:
            row.value = value
        else:
            db.add(models.SiteSetting(key=f"reviews_{key}", value=value))
    db.commit()
    return _payload(db)


@admin_router.post("/items")
def add_review(payload: ReviewIn, db: Session = Depends(get_db)):
    db.add(
        models.ReviewItem(
            author=payload.author.strip(),
            rating=payload.rating,
            text=(payload.text or "").strip() or None,
            when_text=(payload.when or "").strip() or None,
        )
    )
    db.commit()
    return _payload(db)


@admin_router.delete("/items/{review_id}")
def delete_review(review_id: int, db: Session = Depends(get_db)):
    row = db.query(models.ReviewItem).filter(models.ReviewItem.id == review_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Review not found")
    db.delete(row)
    db.commit()
    return _payload(db)
