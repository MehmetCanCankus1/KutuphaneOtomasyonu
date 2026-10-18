# Üniversite Online Kütüphane Yönetim Sistemi - uygulamanın giriş noktası
# Çalıştırmak için: uvicorn main:app --reload
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api_package import hata_yoneticilerini_kaydet, router
from domain_package import (
    CezaBorc,
    GUNLUK_CEZA_TL,
    Kitap,
    Odunc,
    SessionLocal,
    Uye,
    init_db,
)

WEB_DIZINI = Path(__file__).resolve().parent / "web_package"


def seed_data() -> None:
    # Veritabanı boşsa örnek kitap, üye, ödünç ve ceza kayıtlarını ekler
    db = SessionLocal()
    try:
        if db.query(Uye).count() > 0 or db.query(Kitap).count() > 0:
            return
        bugun = date.today()

        # Kitaplar (Algoritmalara Giriş'in stoğu 1, ödünç verilince 0 oluyor)
        kitaplar = [
            Kitap(isbn="9780132350884", baslik="Clean Code", yazar="Robert C. Martin", kategori="Yazılım", stokAdedi=3),
            Kitap(isbn="9786053609421", baslik="Suç ve Ceza", yazar="Fyodor Dostoyevski", kategori="Roman", stokAdedi=3),
            Kitap(isbn="9786055029128", baslik="Sapiens: İnsan Türünün Kısa Tarihi", yazar="Yuval Noah Harari", kategori="Tarih", stokAdedi=2),
            Kitap(isbn="9780262046305", baslik="Algoritmalara Giriş", yazar="Thomas H. Cormen", kategori="Bilgisayar Bilimleri", stokAdedi=1),
            Kitap(isbn="9789750807145", baslik="Nutuk", yazar="Mustafa Kemal Atatürk", kategori="Tarih", stokAdedi=4),
        ]
        for k in kitaplar:
            k.kitapEkle(db)
        clean, suc, sapiens, algo, nutuk = kitaplar

        # Üyeler
        yonetici = Uye(adSoyad="Dr. Selin Kütüphaneci", ogrenciNo="PER-0001", email="selin.k@universite.edu.tr", rol="Yonetici", toplamBorc=0.0)
        ayse = Uye(adSoyad="Ayşe Yılmaz", ogrenciNo="20210001", email="ayse.yilmaz@ogr.universite.edu.tr", rol="Ogrenci", toplamBorc=0.0)
        mehmet = Uye(adSoyad="Mehmet Demir", ogrenciNo="20210002", email="mehmet.demir@ogr.universite.edu.tr", rol="Ogrenci", toplamBorc=0.0)
        zeynep = Uye(adSoyad="Zeynep Kaya", ogrenciNo="20210003", email="zeynep.kaya@ogr.universite.edu.tr", rol="Ogrenci", toplamBorc=0.0)
        db.add_all([yonetici, ayse, mehmet, zeynep])
        db.flush()

        # Ayşe: teslim tarihi geçmiş, hâlâ iade etmemiş (Clean Code)
        clean.stokAzalt()
        db.add(Odunc(uyeId=ayse.uyeId, kitapId=clean.kitapId,
                     alisTarihi=bugun - timedelta(days=25), sonTeslimTarihi=bugun - timedelta(days=11),
                     iadeTarihi=None, aktifMi=True))

        # Ayşe: geçmişte 6 gün geç iade etmiş, 60 TL borcu ödenmemiş
        gecmis = Odunc(uyeId=ayse.uyeId, kitapId=sapiens.kitapId,
                       alisTarihi=bugun - timedelta(days=40), sonTeslimTarihi=bugun - timedelta(days=26),
                       iadeTarihi=bugun - timedelta(days=20), aktifMi=False)
        db.add(gecmis)
        db.flush()
        CezaBorc.cezaOlustur(gecmis, gecmis.gecikmeHesapla())

        # Mehmet: zamanında, aktif ödünç (Algoritmalara Giriş, stok 0 olur)
        algo.stokAzalt()
        db.add(Odunc(uyeId=mehmet.uyeId, kitapId=algo.kitapId,
                     alisTarihi=bugun - timedelta(days=3), sonTeslimTarihi=bugun + timedelta(days=11),
                     iadeTarihi=None, aktifMi=True))

        # Zeynep: zamanında iade (Nutuk) ve 3 gün geç iade edip cezasını ödemiş (Suç ve Ceza)
        db.add(Odunc(uyeId=zeynep.uyeId, kitapId=nutuk.kitapId,
                     alisTarihi=bugun - timedelta(days=30), sonTeslimTarihi=bugun - timedelta(days=16),
                     iadeTarihi=bugun - timedelta(days=20), aktifMi=False))
        zeynep_gec = Odunc(uyeId=zeynep.uyeId, kitapId=suc.kitapId,
                           alisTarihi=bugun - timedelta(days=50), sonTeslimTarihi=bugun - timedelta(days=36),
                           iadeTarihi=bugun - timedelta(days=33), aktifMi=False)
        db.add(zeynep_gec)
        db.flush()
        ceza = CezaBorc.cezaOlustur(zeynep_gec, zeynep_gec.gecikmeHesapla())
        ceza.odemeAl(bugun - timedelta(days=30))

        db.commit()
        print(f"[seed] Örnek veriler eklendi (günlük ceza: {GUNLUK_CEZA_TL:.0f} TL).")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    seed_data()
    yield


app = FastAPI(
    title="Üniversite Online Kütüphane Yönetim Sistemi",
    description="Uye, Kitap, Odunc ve CezaBorc sınıflarından oluşan OOP tabanlı REST API.",
    version="1.0.0",
    lifespan=lifespan,
)
hata_yoneticilerini_kaydet(app)
app.include_router(router)
app.mount("/static", StaticFiles(directory=WEB_DIZINI / "static"), name="static")


@app.get("/", include_in_schema=False)
def anasayfa():
    return FileResponse(WEB_DIZINI / "index.html")


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
