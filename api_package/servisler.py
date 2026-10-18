# İş mantığı servisleri: domain nesnelerini kullanır ve işlemleri kaydeder (commit)
from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from domain_package import (
    CezaBorc,
    GUNLUK_CEZA_TL,
    Kitap,
    KayitBulunamadiHatasi,
    Odunc,
    Uye,
    CakismaHatasi,
)

from . import schemas


# Model nesnelerini şemalara çeviren yardımcı fonksiyonlar
def oduncDetay(o: Odunc) -> schemas.OduncOut:
    gun = o.gecikmeHesapla()
    return schemas.OduncOut(
        oduncId=o.oduncId,
        uyeId=o.uyeId,
        kitapId=o.kitapId,
        uyeAdSoyad=o.uye.adSoyad,
        kitapBaslik=o.kitap.baslik,
        alisTarihi=o.alisTarihi,
        sonTeslimTarihi=o.sonTeslimTarihi,
        iadeTarihi=o.iadeTarihi,
        aktifMi=o.aktifMi,
        gecikmeGunSayisi=gun,
        gecikmisMi=gun > 0,
        tahminiCeza=round(gun * GUNLUK_CEZA_TL, 2) if o.aktifMi else 0.0,
    )


def cezaDetay(c: CezaBorc) -> schemas.CezaOut:
    return schemas.CezaOut(
        cezaId=c.cezaId,
        oduncId=c.oduncId,
        uyeId=c.uyeId,
        uyeAdSoyad=c.uye.adSoyad,
        kitapBaslik=c.odunc.kitap.baslik,
        gecikmeGunSayisi=c.gecikmeGunSayisi,
        tutar=c.tutar,
        odendiMi=c.odendiMi,
        odemeTarihi=c.odemeTarihi,
    )


# Servis sınıfları
class UyeServisi:
    def __init__(self, db: Session):
        self.db = db

    def getir(self, uyeId: int) -> Uye:
        uye = self.db.get(Uye, uyeId)
        if uye is None:
            raise KayitBulunamadiHatasi(f"{uyeId} numaralı üye bulunamadı.")
        return uye

    def listele(self) -> List[Uye]:
        return self.db.query(Uye).order_by(Uye.uyeId).all()

    def olustur(self, veri: schemas.UyeOlustur) -> Uye:
        if self.db.query(Uye).filter((Uye.ogrenciNo == veri.ogrenciNo) | (Uye.email == veri.email)).first():
            raise CakismaHatasi("Bu öğrenci numarası veya e-posta zaten kayıtlı.")
        uye = Uye(adSoyad=veri.adSoyad, ogrenciNo=veri.ogrenciNo, email=veri.email, rol=veri.rol, toplamBorc=0.0)
        self.db.add(uye)
        self.db.commit()
        self.db.refresh(uye)
        return uye

    def kitapAra(self, uyeId: int, kelime: str) -> List[Kitap]:
        return self.getir(uyeId).kitapAra(kelime)


class KitapServisi:
    def __init__(self, db: Session):
        self.db = db

    def getir(self, kitapId: int) -> Kitap:
        kitap = self.db.get(Kitap, kitapId)
        if kitap is None:
            raise KayitBulunamadiHatasi(f"{kitapId} numaralı kitap bulunamadı.")
        return kitap

    def ara(self, kelime: Optional[str], kategori: Optional[str]) -> List[Kitap]:
        return Kitap.ara(self.db, kelime, kategori)

    def kategoriler(self) -> List[str]:
        satirlar = self.db.query(Kitap.kategori).distinct().order_by(Kitap.kategori).all()
        return [s[0] for s in satirlar]

    def ekle(self, veri: schemas.KitapOlustur) -> Kitap:
        kitap = Kitap(**veri.model_dump())
        kitap.kitapEkle(self.db)
        self.db.commit()
        self.db.refresh(kitap)
        return kitap

    def guncelle(self, kitapId: int, veri: schemas.KitapGuncelle) -> Kitap:
        kitap = self.getir(kitapId)
        kitap.kitapGuncelle(**veri.model_dump(exclude_unset=True))
        self.db.commit()
        self.db.refresh(kitap)
        return kitap


class OduncServisi:
    def __init__(self, db: Session):
        self.db = db

    def getir(self, oduncId: int) -> Odunc:
        odunc = self.db.get(Odunc, oduncId)
        if odunc is None:
            raise KayitBulunamadiHatasi(f"{oduncId} numaralı ödünç kaydı bulunamadı.")
        return odunc

    def listele(self, aktif: Optional[bool] = None, uyeId: Optional[int] = None) -> List[Odunc]:
        sorgu = self.db.query(Odunc)
        if aktif is not None:
            sorgu = sorgu.filter(Odunc.aktifMi.is_(aktif))
        if uyeId is not None:
            sorgu = sorgu.filter(Odunc.uyeId == uyeId)
        return sorgu.order_by(Odunc.aktifMi.desc(), Odunc.sonTeslimTarihi, Odunc.oduncId).all()

    def oduncVer(self, veri: schemas.OduncOlustur) -> Odunc:
        uye = UyeServisi(self.db).getir(veri.uyeId)
        odunc = uye.oduncAl(veri.kitapId, veri.gunSayisi)
        self.db.commit()
        self.db.refresh(odunc)
        return odunc

    def iadeAl(self, oduncId: int, simulasyonGun: int = 0) -> schemas.IadeSonuc:
        # simulasyonGun > 0 ise iade tarihi, son teslim tarihinden o kadar gün sonrası alınır
        odunc = self.getir(oduncId)
        iadeTarihi = (
            odunc.sonTeslimTarihi + timedelta(days=simulasyonGun) if simulasyonGun > 0 else date.today()
        )
        ceza = odunc.iadeEt(iadeTarihi)
        self.db.commit()
        self.db.refresh(odunc)
        if ceza is not None:
            self.db.refresh(ceza)
            mesaj = (
                f"Kitap iade alındı. {ceza.gecikmeGunSayisi} gün gecikme nedeniyle "
                f"{ceza.tutar:.2f} TL ceza oluşturuldu."
            )
            return schemas.IadeSonuc(odunc=oduncDetay(odunc), ceza=cezaDetay(ceza), mesaj=mesaj)
        return schemas.IadeSonuc(odunc=oduncDetay(odunc), ceza=None, mesaj="Kitap zamanında iade alındı. Stok güncellendi.")


class BorcServisi:
    def __init__(self, db: Session):
        self.db = db

    def cezalar(self, uyeId: Optional[int] = None, odendiMi: Optional[bool] = None) -> List[CezaBorc]:
        sorgu = self.db.query(CezaBorc)
        if uyeId is not None:
            sorgu = sorgu.filter(CezaBorc.uyeId == uyeId)
        if odendiMi is not None:
            sorgu = sorgu.filter(CezaBorc.odendiMi.is_(odendiMi))
        return sorgu.order_by(CezaBorc.odendiMi, CezaBorc.cezaId).all()

    def cezaOde(self, cezaId: int) -> schemas.CezaOdemeSonuc:
        ceza = self.db.get(CezaBorc, cezaId)
        if ceza is None:
            raise KayitBulunamadiHatasi(f"{cezaId} numaralı ceza kaydı bulunamadı.")
        ceza.odemeAl()
        self.db.commit()
        self.db.refresh(ceza)
        return schemas.CezaOdemeSonuc(
            ceza=cezaDetay(ceza),
            uye=schemas.UyeOut.model_validate(ceza.uye),
            mesaj=f"{ceza.tutar:.2f} TL ceza ödemesi alındı.",
        )

    def borcOde(self, uyeId: int, miktar: Optional[float]) -> schemas.BorcOdemeSonuc:
        uye = UyeServisi(self.db).getir(uyeId)
        odenecek = miktar if miktar is not None else uye.toplamBorc
        odenen = uye.borcOde(odenecek)
        self.db.commit()
        self.db.refresh(uye)
        return schemas.BorcOdemeSonuc(
            uye=schemas.UyeOut.model_validate(uye),
            odenenMiktar=odenen,
            mesaj=f"{odenen:.2f} TL ödendi. Kalan borç: {uye.toplamBorc:.2f} TL.",
        )


class RaporServisi:
    def __init__(self, db: Session):
        self.db = db

    def gecikmeRaporu(self) -> schemas.GecikmeRaporu:
        bugun = date.today()
        satirlar: List[schemas.RaporSatiri] = []

        geciken = (
            self.db.query(Odunc)
            .filter(Odunc.aktifMi.is_(True), Odunc.sonTeslimTarihi < bugun)
            .order_by(Odunc.sonTeslimTarihi)
            .all()
        )
        for o in geciken:
            gun = o.gecikmeHesapla()
            satirlar.append(schemas.RaporSatiri(
                tur="Geciken (Teslim Edilmedi)",
                oduncId=o.oduncId, uyeId=o.uyeId, uyeAdSoyad=o.uye.adSoyad,
                kitapBaslik=o.kitap.baslik, sonTeslimTarihi=o.sonTeslimTarihi,
                iadeTarihi=None, gecikmeGunSayisi=gun,
                tutar=round(gun * GUNLUK_CEZA_TL, 2), durum="Teslim Edilmedi",
            ))

        cezalar = self.db.query(CezaBorc).order_by(CezaBorc.odendiMi, CezaBorc.cezaId.desc()).all()
        for c in cezalar:
            satirlar.append(schemas.RaporSatiri(
                tur="Cezalı İade",
                oduncId=c.oduncId, cezaId=c.cezaId, uyeId=c.uyeId, uyeAdSoyad=c.uye.adSoyad,
                kitapBaslik=c.odunc.kitap.baslik, sonTeslimTarihi=c.odunc.sonTeslimTarihi,
                iadeTarihi=c.odunc.iadeTarihi, gecikmeGunSayisi=c.gecikmeGunSayisi,
                tutar=c.tutar, durum="Ceza Ödendi" if c.odendiMi else "Ceza Ödenmedi",
            ))

        return schemas.GecikmeRaporu(
            gecikenAktifSayisi=len(geciken),
            cezaliKayitSayisi=len(cezalar),
            toplamCeza=round(sum(c.tutar for c in cezalar), 2),
            odenmemisCeza=round(sum(c.tutar for c in cezalar if not c.odendiMi), 2),
            satirlar=satirlar,
        )

    def ozet(self) -> schemas.Ozet:
        db = self.db
        bugun = date.today()
        return schemas.Ozet(
            toplamKitapCesidi=db.query(func.count(Kitap.kitapId)).scalar() or 0,
            toplamStok=db.query(func.coalesce(func.sum(Kitap.stokAdedi), 0)).scalar() or 0,
            aktifOdunc=db.query(func.count(Odunc.oduncId)).filter(Odunc.aktifMi.is_(True)).scalar() or 0,
            gecikenOdunc=db.query(func.count(Odunc.oduncId))
            .filter(Odunc.aktifMi.is_(True), Odunc.sonTeslimTarihi < bugun).scalar() or 0,
            toplamUye=db.query(func.count(Uye.uyeId)).scalar() or 0,
            toplamBorc=round(db.query(func.coalesce(func.sum(Uye.toplamBorc), 0.0)).scalar() or 0.0, 2),
        )
