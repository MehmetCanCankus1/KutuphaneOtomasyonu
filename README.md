# Üniversite Online Kütüphane Yönetim Sistemi

Bu proje, bir üniversite kütüphanesinin kitap, üye, ödünç verme ve gecikme cezası işlemlerini yönetmek için hazırlanmış bir ders projesidir. Nesne yönelimli programlama (OOP) ilkelerine ve UML sınıf diyagramına uygun olarak geliştirilmiştir.

## Projenin Amacı

- Kitap ekleme, güncelleme, arama ve stok takibi
- Öğrencilere kitap ödünç verme ve iade alma
- Teslim tarihi geçen kitaplar için günlük 10 TL gecikme cezası hesaplama
- Üyelerin borçlarını görüntüleme ve ödeme alma
- Gecikme raporu oluşturma

## Kullanılan Teknolojiler

| Katman | Teknoloji |
|---|---|
| Programlama dili | Python 3 |
| API | FastAPI |
| Veritabanı | SQLite + SQLAlchemy (ORM) |
| Doğrulama | Pydantic |
| Arayüz | HTML5, TailwindCSS (CDN), JavaScript (Fetch API) |

## Paket Yapısı

Proje üç mantıksal pakete ayrılmıştır:

```
KutuphaneOtomasyonu/
├── domain_package/     # Modeller ve veritabanı
│   ├── database.py
│   ├── istisnalar.py
│   ├── uye.py
│   ├── kitap.py
│   ├── odunc.py
│   └── cezaborc.py
├── api_package/        # İş mantığı servisleri ve REST API
│   ├── schemas.py
│   ├── servisler.py
│   └── routers.py
├── web_package/        # Web arayüzü
│   ├── index.html
│   └── static/
│       ├── app.js
│       └── style.css
├── main.py             # Uygulamanın başlangıç dosyası
└── requirements.txt
```

### domain_package

UML sınıf diyagramındaki dört sınıfı içerir:

| Sınıf | Metotlar |
|---|---|
| `Uye` | `kitapAra(kelime)`, `oduncAl(kitapId)`, `borcOde(miktar)` |
| `Kitap` | `kitapEkle()`, `kitapGuncelle()`, `stokAzalt()`, `stokArtir()` |
| `Odunc` | `iadeEt()`, `gecikmeHesapla()` |
| `CezaBorc` | `cezaOlustur()`, `odemeAl()` |

### api_package

Servis sınıfları iş kurallarını uygular, `routers.py` ise REST endpointlerini tanımlar. Endpointlerin dokümantasyonuna uygulama çalışırken `/docs` adresinden ulaşılabilir.

### web_package

Yönetici ve öğrenci için tek sayfalık arayüz. Sağ üstteki listeden kullanıcı seçilerek rol değiştirilebilir (giriş sistemi yoktur).

- **Yönetici:** Panel, Kitaplar, Ödünç / İade, Borç Ödeme, Gecikme Raporu, Üyeler
- **Öğrenci:** Kitaplar, Ödünçlerim, Borçlarım

## Kurulum ve Çalıştırma

1. Projeyi indirin ve klasöre girin.

2. (İsteğe bağlı) Sanal ortam oluşturun:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Gerekli paketleri kurun:

   ```bash
   pip install -r requirements.txt
   ```

4. Uygulamayı başlatın:

   ```bash
   uvicorn main:app --reload
   ```

5. Tarayıcıdan `http://127.0.0.1:8000` adresini açın. API dokümantasyonu `http://127.0.0.1:8000/docs` adresindedir.

Uygulama ilk çalıştığında `kutuphane.db` dosyası otomatik oluşturulur ve içine örnek veriler (5 kitap, 1 yönetici, 3 öğrenci, ödünç ve ceza kayıtları) eklenir. Verileri sıfırlamak için uygulamayı durdurup `kutuphane.db` dosyasını silmeniz yeterlidir.

## Gecikme ve Ceza Mantığı

- Ödünç süresi varsayılan olarak 14 gündür.
- İade tarihi son teslim tarihinden sonraysa gecikme günü × 10 TL tutarında `CezaBorc` kaydı oluşur ve üyenin `toplamBorc` değerine eklenir.
- Arayüzde test amacıyla **"5 Gün Gecikmeli İade Et"** butonu bulunur; kitabı son teslim tarihinden 5 gün sonra iade edilmiş gibi işler (50 TL ceza).
- Stoğu 0 olan bir kitap ödünç verilmek istenirse uyarı döner.
