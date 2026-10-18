# REST API endpointleri
from typing import List, Optional

from fastapi import APIRouter, Depends, FastAPI, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from domain_package import KutuphaneHatasi, get_db

from . import schemas
from .servisler import (
    BorcServisi,
    KitapServisi,
    OduncServisi,
    RaporServisi,
    UyeServisi,
    cezaDetay,
    oduncDetay,
)

router = APIRouter(prefix="/api")


def hata_yoneticilerini_kaydet(app: FastAPI) -> None:
    # Domain hatalarını HTTP durum koduyla JSON olarak döndürür

    @app.exception_handler(KutuphaneHatasi)
    async def _kutuphane_hatasi(_, exc: KutuphaneHatasi):
        return JSONResponse(status_code=exc.kod, content={"detail": str(exc)})


# Üyeler
@router.get("/uyeler", response_model=List[schemas.UyeOut], tags=["Üye"])
def uyeleri_listele(db: Session = Depends(get_db)):
    return UyeServisi(db).listele()


@router.get("/uyeler/{uyeId}", response_model=schemas.UyeOut, tags=["Üye"])
def uye_getir(uyeId: int, db: Session = Depends(get_db)):
    return UyeServisi(db).getir(uyeId)


@router.post("/uyeler", response_model=schemas.UyeOut, status_code=201, tags=["Üye"])
def uye_olustur(veri: schemas.UyeOlustur, db: Session = Depends(get_db)):
    return UyeServisi(db).olustur(veri)


@router.get("/uyeler/{uyeId}/kitap-ara", response_model=List[schemas.KitapOut], tags=["Üye"])
def uye_kitap_ara(uyeId: int, kelime: str = "", db: Session = Depends(get_db)):
    # Uye.kitapAra(kelime)
    return UyeServisi(db).kitapAra(uyeId, kelime)


@router.post("/uyeler/{uyeId}/borc-ode", response_model=schemas.BorcOdemeSonuc, tags=["Borç"])
def uye_borc_ode(uyeId: int, istek: Optional[schemas.BorcOdeIstegi] = None, db: Session = Depends(get_db)):
    # Uye.borcOde(miktar), miktar gelmezse borcun tamamı ödenir
    return BorcServisi(db).borcOde(uyeId, istek.miktar if istek else None)


# Kitaplar
@router.get("/kitaplar", response_model=List[schemas.KitapOut], tags=["Kitap"])
def kitaplari_ara(
    arama: Optional[str] = Query(None, description="Başlık, yazar, kategori veya ISBN"),
    kategori: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return KitapServisi(db).ara(arama, kategori)


@router.get("/kategoriler", response_model=List[str], tags=["Kitap"])
def kategorileri_listele(db: Session = Depends(get_db)):
    return KitapServisi(db).kategoriler()


@router.get("/kitaplar/{kitapId}", response_model=schemas.KitapOut, tags=["Kitap"])
def kitap_getir(kitapId: int, db: Session = Depends(get_db)):
    return KitapServisi(db).getir(kitapId)


@router.post("/kitaplar", response_model=schemas.KitapOut, status_code=201, tags=["Kitap"])
def kitap_ekle(veri: schemas.KitapOlustur, db: Session = Depends(get_db)):
    # Kitap.kitapEkle()
    return KitapServisi(db).ekle(veri)


@router.put("/kitaplar/{kitapId}", response_model=schemas.KitapOut, tags=["Kitap"])
def kitap_guncelle(kitapId: int, veri: schemas.KitapGuncelle, db: Session = Depends(get_db)):
    # Kitap.kitapGuncelle()
    return KitapServisi(db).guncelle(kitapId, veri)


# Ödünç işlemleri
@router.get("/odunc", response_model=List[schemas.OduncOut], tags=["Ödünç"])
def oduncleri_listele(aktif: Optional[bool] = None, uyeId: Optional[int] = None, db: Session = Depends(get_db)):
    return [oduncDetay(o) for o in OduncServisi(db).listele(aktif, uyeId)]


@router.post("/odunc", response_model=schemas.OduncOut, status_code=201, tags=["Ödünç"])
def odunc_ver(veri: schemas.OduncOlustur, db: Session = Depends(get_db)):
    # Uye.oduncAl(kitapId): stok bir azalır, stok 0 ise 409 döner
    return oduncDetay(OduncServisi(db).oduncVer(veri))


@router.post("/odunc/{oduncId}/iade", response_model=schemas.IadeSonuc, tags=["Ödünç"])
def odunc_iade(
    oduncId: int,
    simulasyon_gun: int = Query(0, ge=0, le=365, description="Gecikmeli iade simülasyonu: son teslimden kaç gün sonra"),
    db: Session = Depends(get_db),
):
    # Odunc.iadeEt(): stok bir artar, gecikme varsa ceza kaydı oluşur
    return OduncServisi(db).iadeAl(oduncId, simulasyon_gun)


# Ceza ve borç
@router.get("/cezalar", response_model=List[schemas.CezaOut], tags=["Borç"])
def cezalari_listele(uyeId: Optional[int] = None, odendiMi: Optional[bool] = None, db: Session = Depends(get_db)):
    return [cezaDetay(c) for c in BorcServisi(db).cezalar(uyeId, odendiMi)]


@router.post("/cezalar/{cezaId}/ode", response_model=schemas.CezaOdemeSonuc, tags=["Borç"])
def ceza_ode(cezaId: int, db: Session = Depends(get_db)):
    # CezaBorc.odemeAl()
    return BorcServisi(db).cezaOde(cezaId)


# Raporlar
@router.get("/rapor/gecikme", response_model=schemas.GecikmeRaporu, tags=["Rapor"])
def gecikme_raporu(db: Session = Depends(get_db)):
    return RaporServisi(db).gecikmeRaporu()


@router.get("/ozet", response_model=schemas.Ozet, tags=["Rapor"])
def ozet(db: Session = Depends(get_db)):
    return RaporServisi(db).ozet()
