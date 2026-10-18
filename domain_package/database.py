# Veritabanı bağlantısı (SQLite + SQLAlchemy)
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

PROJE_DIZINI = Path(__file__).resolve().parent.parent
VERITABANI_YOLU = PROJE_DIZINI / "kutuphane.db"
VERITABANI_URL = f"sqlite:///{VERITABANI_YOLU}"

engine = create_engine(VERITABANI_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Tüm model sınıfları bu sınıftan türer
Base = declarative_base()


def get_db():
    # Her istek için bir oturum açar, iş bitince kapatır
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    # Modeller import edilmeden tablolar oluşturulamaz
    from . import cezaborc, kitap, odunc, uye

    Base.metadata.create_all(bind=engine)
