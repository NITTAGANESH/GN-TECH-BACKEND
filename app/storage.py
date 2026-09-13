import uuid

from supabase import create_client, Client

from .config import settings

_client: Client | None = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_service_key)
    return _client


def upload_image(file_bytes: bytes, filename: str, content_type: str) -> tuple[str, str]:
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
    storage_path = f"{uuid.uuid4().hex}.{ext}"

    client = get_supabase()
    bucket = client.storage.from_(settings.supabase_storage_bucket)
    bucket.upload(
        storage_path,
        file_bytes,
        file_options={"content-type": content_type},
    )
    public_url = bucket.get_public_url(storage_path)
    return public_url, storage_path


def delete_image(storage_path: str) -> None:
    client = get_supabase()
    client.storage.from_(settings.supabase_storage_bucket).remove([storage_path])


def upload_pdf(file_bytes: bytes, filename: str) -> tuple[str, str]:
    storage_path = f"bills/{filename}"

    client = get_supabase()
    bucket = client.storage.from_(settings.supabase_storage_bucket)
    bucket.upload(
        storage_path,
        file_bytes,
        file_options={"content-type": "application/pdf"},
    )
    public_url = bucket.get_public_url(storage_path)
    return public_url, storage_path
