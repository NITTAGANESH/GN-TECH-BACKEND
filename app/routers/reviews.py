import time

import httpx
from fastapi import APIRouter

from ..config import settings

router = APIRouter(prefix="/api/reviews", tags=["reviews"])

CACHE_TTL_SECONDS = 6 * 60 * 60  # Google data barely changes; keeps API usage tiny
_cache: dict = {"data": None, "fetched_at": 0.0}
_resolved_place_id: str | None = None


def _resolve_place_id(client: httpx.Client) -> str | None:
    global _resolved_place_id
    if settings.google_place_id:
        return settings.google_place_id
    if _resolved_place_id:
        return _resolved_place_id

    resp = client.post(
        "https://places.googleapis.com/v1/places:searchText",
        headers={
            "X-Goog-Api-Key": settings.google_places_api_key,
            "X-Goog-FieldMask": "places.id",
        },
        json={"textQuery": settings.google_place_query},
    )
    resp.raise_for_status()
    places = resp.json().get("places", [])
    if places:
        _resolved_place_id = places[0]["id"]
    return _resolved_place_id


def _fetch_from_google() -> dict:
    with httpx.Client(timeout=15) as client:
        place_id = _resolve_place_id(client)
        if not place_id:
            raise RuntimeError("Could not find the business on Google Places")

        resp = client.get(
            f"https://places.googleapis.com/v1/places/{place_id}",
            headers={
                "X-Goog-Api-Key": settings.google_places_api_key,
                "X-Goog-FieldMask": "rating,userRatingCount,reviews,googleMapsUri",
            },
        )
        resp.raise_for_status()
        place = resp.json()

    reviews = []
    for r in place.get("reviews", []):
        author = r.get("authorAttribution", {})
        text = (r.get("text") or r.get("originalText") or {}).get("text", "")
        reviews.append(
            {
                "author": author.get("displayName", "Google user"),
                "photo": author.get("photoUri"),
                "rating": r.get("rating", 5),
                "text": text,
                "when": r.get("relativePublishTimeDescription", ""),
            }
        )

    return {
        "configured": True,
        "rating": place.get("rating"),
        "total": place.get("userRatingCount"),
        "maps_url": place.get("googleMapsUri"),
        "reviews": reviews,
    }


@router.get("")
def get_reviews():
    if not settings.google_places_api_key:
        return {"configured": False}

    now = time.time()
    if _cache["data"] and now - _cache["fetched_at"] < CACHE_TTL_SECONDS:
        return _cache["data"]

    try:
        data = _fetch_from_google()
    except Exception:
        # Serve stale data rather than failing the page if Google hiccups.
        if _cache["data"]:
            return _cache["data"]
        return {"configured": False}

    _cache["data"] = data
    _cache["fetched_at"] = now
    return data
