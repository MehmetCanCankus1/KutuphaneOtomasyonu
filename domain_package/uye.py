from datetime import date, timedelta
from typing import List

from sqlalchemy import Column, Float, Integer, String
from sqlalchemy.orm import object_session, relationship

from .database import Base
from .istisnalar import CakismaHatasi, KayitBulunamadiHatasi, KutuphaneHatasi
from .kitap import Kitap
from .odunc import Odunc

ROL_OGRENCI = "Ogrenci"
ROL_YONETICI = "Yonetici"
VARSAYILAN_ODUNC_GUNU = 14


class Uye(Base):
    __tablename__ = "uyeler"

    uyeId = Column(Integer, primary_key=True, autoincrement=True)
    adSoyad = Column(String(120), nullable=False)
    ogrenciNo = Column(String(30), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    rol = Column(String(20), nullable=False, default=ROL_OGRENCI)
    toplamBorc = Column(Float, nullable=False, default=0.0)

    oduncler = relationship("Odunc", back_populates="uye")
    cezalar = relationship("CezaBorc", back_populates="uye")

    def kitapAra(self, kelime: str) -> List[Kitap]:
        db = object_session(self)
        if db is None:
            raise KutuphaneHatasi("Arama için üye bir oturuma bağlı olmalı.")
        return Kitap.ara(db, kelime)

    def oduncAl(self, kitapId: int, gunSayisi: int = VARSAYILAN_ODUNC_GUNU) -> Odunc:
        db = object_session(self)
        if db is None:
            raise KutuphaneHatasi("Ödünç almak için üye bir oturuma bağlı olmalı.")
        kitap = db.get(Kitap, kitapId)
        if kitap is None:
            raise KayitBulunamadiHatasi(f"{kitapId} numaralı kitap bulunamadı.")
        # Aynı kitap aynı üyede iki kez ödünçte olamaz
        zaten = (
            db.query(Odunc)
            .filter(Odunc.uyeId == self.uyeId, Odunc.kitapId == kitapId, Odunc.aktifMi.is_(True))
            .first()
        )
        if zaten:
            raise CakismaHatasi(f"'{kitap.baslik}' kitabı bu üyede zaten ödünçte.")
        kitap.stokAzalt()  # stok 0 ise hata verir
        bugun = date.today()
        odunc = Odunc(
            uyeId=self.uyeId,
            kitapId=kitapId,
            alisTarihi=bugun,
            sonTeslimTarihi=bugun + timedelta(days=gunSayisi),
            aktifMi=True,
        )
        db.add(odunc)
        db.flush()
        return odunc

    def borcOde(self, miktar: float) -> float:
        # Ödeme en eski cezadan başlayarak kapatılır.
        # Son ceza tam karşılanamazsa tutarı kalan miktara düşürülür.
        if miktar is None or miktar <= 0:
            raise KutuphaneHatasi("Ödeme miktarı sıfırdan büyük olmalı.")
        borc = round(self.toplamBorc or 0.0, 2)
        if borc <= 0:
            raise KutuphaneHatasi("Üyenin ödenecek borcu bulunmuyor.")
        miktar = round(miktar, 2)
        if miktar > borc + 0.001:
            raise KutuphaneHatasi(f"Ödeme miktarı toplam borcu ({borc:.2f} TL) aşamaz.")

        kalan = miktar
        acik = sorted((c for c in self.cezalar if not c.odendiMi), key=lambda c: c.cezaId)
        for ceza in acik:
            if kalan + 0.001 >= ceza.tutar:
                kalan = round(kalan - ceza.tutar, 2)
                ceza.odemeAl()
            else:
                break
        if kalan > 0.001:
            kismi = next((c for c in acik if not c.odendiMi), None)
            if kismi is not None:
                kismi.tutar = round(kismi.tutar - kalan, 2)
            self.toplamBorc = max(0.0, round((self.toplamBorc or 0.0) - kalan, 2))
        return miktar

    def __repr__(self) -> str:
        return f"<Uye {self.uyeId} {self.adSoyad!r} rol={self.rol} borc={self.toplamBorc}>"
