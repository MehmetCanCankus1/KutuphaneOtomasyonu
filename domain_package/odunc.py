from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer
from sqlalchemy.orm import relationship

from .cezaborc import CezaBorc
from .database import Base
from .istisnalar import KutuphaneHatasi


class Odunc(Base):
    __tablename__ = "oduncler"

    oduncId = Column(Integer, primary_key=True, autoincrement=True)
    uyeId = Column(Integer, ForeignKey("uyeler.uyeId"), nullable=False)
    kitapId = Column(Integer, ForeignKey("kitaplar.kitapId"), nullable=False)
    alisTarihi = Column(Date, nullable=False, default=date.today)
    sonTeslimTarihi = Column(Date, nullable=False)
    iadeTarihi = Column(Date, nullable=True)
    aktifMi = Column(Boolean, nullable=False, default=True)

    uye = relationship("Uye", back_populates="oduncler")
    kitap = relationship("Kitap", back_populates="oduncler")
    cezalar = relationship("CezaBorc", back_populates="odunc")

    def gecikmeHesapla(self, referansTarih: Optional[date] = None) -> int:
        # İade edilmişse iade tarihine, edilmemişse bugüne göre gecikme günü
        bitis = self.iadeTarihi or referansTarih or date.today()
        return max(0, (bitis - self.sonTeslimTarihi).days)

    def iadeEt(self, iadeTarihi: Optional[date] = None) -> Optional[CezaBorc]:
        # Kitabı iade alır, stoğu artırır. Gecikme varsa ceza kaydı döner
        if not self.aktifMi:
            raise KutuphaneHatasi("Bu ödünç kaydı zaten iade edilmiş.")
        self.iadeTarihi = iadeTarihi or date.today()
        self.aktifMi = False
        self.kitap.stokArtir()
        gun = self.gecikmeHesapla()
        if gun > 0:
            return CezaBorc.cezaOlustur(self, gun)
        return None

    def __repr__(self) -> str:
        return f"<Odunc {self.oduncId} uye={self.uyeId} kitap={self.kitapId} aktif={self.aktifMi}>"
