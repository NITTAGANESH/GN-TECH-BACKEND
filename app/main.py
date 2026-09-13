from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from . import models  # noqa: F401 (ensures models are registered before create_all)
from .routers import contacts, feedback, chat, uploads

Base.metadata.create_all(bind=engine)

app = FastAPI(title="GN Tech Solutions API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(contacts.router)
app.include_router(feedback.router)
app.include_router(chat.router)
app.include_router(uploads.router)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "gn-tech-solutions-api"}
