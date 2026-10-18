from typing import List, Optional

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Session, object_session, relationship

from .database import Base
from .istisnalar import CakismaHatasi, KutuphaneHatasi, StokYokHatasi

# Aramada Türkçe karakter ve büyük/küçük harf farkı olmasın diye
_TR_SADELESTIR = str.maketrans("ıçğöşü", "icgosu")


def _normalize(metin: str) -> str:
    metin = (metin or "").replace("İ", "i").replace("I", "i").lower()
    return metin.translate(_TR_SADELESTIR).strip()


class Kitap(Base):
    __tablename__ = "kitaplar"

    kitapId = Column(Integer, primary_key=True, autoincrement=True)
    isbn = Column(String(20), unique=True, nullable=False)
    baslik = Column(String(200), nullable=False)
    yazar = Column(String(120), nullable=False)
    kategori = Column(String(80), nullable=False)
    stokAdedi = Column(Integer, nullable=False, default=0)

    oduncler = relationship("Odunc", back_populates="kitap")

    GUNCELLENEBILIR_ALANLAR = ("isbn", "baslik", "yazar", "kategori", "stokAdedi")

    def kitapEkle(self, db: Optional[Session] = None) -> "Kitap":
        db = db or object_session(self)
        if db is None:
            raise KutuphaneHatasi("Kitap eklemek için veritabanı oturumu gerekli.")
        if (self.stokAdedi or 0) < 0:
            raise KutuphaneHatasi("Stok adedi negatif olamaz.")
        # ISBN tekrar edemez
        if db.query(Kitap).filter(Kitap.isbn == self.isbn).first():
            raise CakismaHatasi(f"{self.isbn} ISBN numaralı kitap zaten kayıtlı.")
        db.add(self)
        db.flush()
        return self

    def kitapGuncelle(self, **alanlar) -> "Kitap":
        db = object_session(self)
        for ad, deger in alanlar.items():
            if ad not in self.GUNCELLENEBILIR_ALANLAR:
                raise KutuphaneHatasi(f"'{ad}' alanı güncellenemez.")
            if deger is None:
                continue
            if ad == "stokAdedi" and deger < 0:
                raise KutuphaneHatasi("Stok adedi negatif olamaz.")
            if ad == "isbn" and db is not None and deger != self.isbn:
                if db.query(Kitap).filter(Kitap.isbn == deger).first():
                    raise CakismaHatasi(f"{deger} ISBN numaralı kitap zaten kayıtlı.")
            setattr(self, ad, deger)
        return self

    def stokAzalt(self, adet: int = 1) -> int:
        if self.stokAdedi < adet:
            raise StokYokHatasi(f"'{self.baslik}' kitabının stoğu tükendi, ödünç verilemez.")
        self.stokAdedi -= adet
        return self.stokAdedi

    def stokArtir(self, adet: int = 1) -> int:
        self.stokAdedi += adet
        return self.stokAdedi

    @classmethod
    def ara(cls, db: Session, kelime: Optional[str] = None, kategori: Optional[str] = None) -> List["Kitap"]:
        # Başlık, yazar, kategori ve ISBN içinde arar
        sorgu = db.query(cls)
        if kategori:
            sorgu = sorgu.filter(cls.kategori == kategori)
        kitaplar = sorgu.order_by(cls.kitapId).all()
        if kelime and kelime.strip():
            k = _normalize(kelime)
            kitaplar = [
                x for x in kitaplar
                if k in _normalize(" ".join([x.baslik, x.yazar, x.kategori, x.isbn]))
            ]
        return kitaplar

    def __repr__(self) -> str:
        return f"<Kitap {self.kitapId} {self.baslik!r} stok={self.stokAdedi}>"
