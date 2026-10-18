from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Column, Date, Float, ForeignKey, Integer
from sqlalchemy.orm import object_session, relationship

from .database import Base
from .istisnalar import KutuphaneHatasi

GUNLUK_CEZA_TL = 10.0


class CezaBorc(Base):
    __tablename__ = "ceza_borclar"

    cezaId = Column(Integer, primary_key=True, autoincrement=True)
    oduncId = Column(Integer, ForeignKey("oduncler.oduncId"), nullable=False)
    uyeId = Column(Integer, ForeignKey("uyeler.uyeId"), nullable=False)
    gecikmeGunSayisi = Column(Integer, nullable=False, default=0)
    tutar = Column(Float, nullable=False, default=0.0)
    odendiMi = Column(Boolean, nullable=False, default=False)
    odemeTarihi = Column(Date, nullable=True)

    odunc = relationship("Odunc", back_populates="cezalar")
    uye = relationship("Uye", back_populates="cezalar")

    @classmethod
    def cezaOlustur(cls, odunc, gecikmeGunSayisi: Optional[int] = None) -> "CezaBorc":
        # Gecikme günü * günlük ceza kadar borç yazılır, üyenin toplam borcuna eklenir
        gun = gecikmeGunSayisi if gecikmeGunSayisi is not None else odunc.gecikmeHesapla()
        if gun <= 0:
            raise KutuphaneHatasi("Gecikme olmadığı için ceza oluşturulamaz.")
        db = object_session(odunc)
        tutar = round(gun * GUNLUK_CEZA_TL, 2)
        ceza = cls(
            oduncId=odunc.oduncId,
            uyeId=odunc.uyeId,
            gecikmeGunSayisi=gun,
            tutar=tutar,
            odendiMi=False,
            odemeTarihi=None,
        )
        if db is not None:
            db.add(ceza)
        odunc.uye.toplamBorc = round((odunc.uye.toplamBorc or 0.0) + tutar, 2)
        if db is not None:
            db.flush()
        return ceza

    def odemeAl(self, odemeTarihi: Optional[date] = None) -> "CezaBorc":
        # Cezayı kapatır, tutarı üyenin borcundan düşer
        if self.odendiMi:
            raise KutuphaneHatasi("Bu ceza zaten ödenmiş.")
        self.odendiMi = True
        self.odemeTarihi = odemeTarihi or date.today()
        self.uye.toplamBorc = max(0.0, round((self.uye.toplamBorc or 0.0) - self.tutar, 2))
        return self

    def __repr__(self) -> str:
        return f"<CezaBorc {self.cezaId} {self.tutar} TL odendi={self.odendiMi}>"
