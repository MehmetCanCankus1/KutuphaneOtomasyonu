# Pydantic şemaları (istek ve yanıt modelleri)
from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class _Orm(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# Kitap
class KitapOlustur(BaseModel):
    isbn: str = Field(..., min_length=3, max_length=20)
    baslik: str = Field(..., min_length=1, max_length=200)
    yazar: str = Field(..., min_length=1, max_length=120)
    kategori: str = Field(..., min_length=1, max_length=80)
    stokAdedi: int = Field(0, ge=0)


class KitapGuncelle(BaseModel):
    isbn: Optional[str] = Field(None, min_length=3, max_length=20)
    baslik: Optional[str] = Field(None, min_length=1, max_length=200)
    yazar: Optional[str] = Field(None, min_length=1, max_length=120)
    kategori: Optional[str] = Field(None, min_length=1, max_length=80)
    stokAdedi: Optional[int] = Field(None, ge=0)


class KitapOut(_Orm):
    kitapId: int
    isbn: str
    baslik: str
    yazar: str
    kategori: str
    stokAdedi: int


# Üye
class UyeOlustur(BaseModel):
    adSoyad: str = Field(..., min_length=2, max_length=120)
    ogrenciNo: str = Field(..., min_length=2, max_length=30)
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    rol: Literal["Ogrenci", "Yonetici"] = "Ogrenci"


class UyeOut(_Orm):
    uyeId: int
    adSoyad: str
    ogrenciNo: str
    email: str
    rol: str
    toplamBorc: float


# Ödünç
class OduncOlustur(BaseModel):
    uyeId: int
    kitapId: int
    gunSayisi: int = Field(14, ge=1, le=90)


class OduncOut(BaseModel):
    oduncId: int
    uyeId: int
    kitapId: int
    uyeAdSoyad: str
    kitapBaslik: str
    alisTarihi: date
    sonTeslimTarihi: date
    iadeTarihi: Optional[date] = None
    aktifMi: bool
    gecikmeGunSayisi: int
    gecikmisMi: bool
    tahminiCeza: float


# Ceza
class CezaOut(BaseModel):
    cezaId: int
    oduncId: int
    uyeId: int
    uyeAdSoyad: str
    kitapBaslik: str
    gecikmeGunSayisi: int
    tutar: float
    odendiMi: bool
    odemeTarihi: Optional[date] = None


class IadeSonuc(BaseModel):
    odunc: OduncOut
    ceza: Optional[CezaOut] = None
    mesaj: str


class BorcOdeIstegi(BaseModel):
    # miktar verilmezse borcun tamamı ödenir
    miktar: Optional[float] = Field(None, gt=0)


class BorcOdemeSonuc(BaseModel):
    uye: UyeOut
    odenenMiktar: float
    mesaj: str


class CezaOdemeSonuc(BaseModel):
    ceza: CezaOut
    uye: UyeOut
    mesaj: str


# Rapor
class RaporSatiri(BaseModel):
    tur: str  # "Geciken (Teslim Edilmedi)" | "Cezalı İade"
    oduncId: int
    cezaId: Optional[int] = None
    uyeId: int
    uyeAdSoyad: str
    kitapBaslik: str
    sonTeslimTarihi: date
    iadeTarihi: Optional[date] = None
    gecikmeGunSayisi: int
    tutar: float
    durum: str  # "Teslim Edilmedi" | "Ceza Ödenmedi" | "Ceza Ödendi"


class GecikmeRaporu(BaseModel):
    gecikenAktifSayisi: int
    cezaliKayitSayisi: int
    toplamCeza: float
    odenmemisCeza: float
    satirlar: List[RaporSatiri]


class Ozet(BaseModel):
    toplamKitapCesidi: int
    toplamStok: int
    aktifOdunc: int
    gecikenOdunc: int
    toplamUye: int
    toplamBorc: float
