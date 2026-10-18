# İş kurallarına aykırı durumlarda fırlatılan hatalar.
# "kod" değeri API katmanında HTTP durum koduna çevriliyor.


class KutuphaneHatasi(Exception):
    kod = 400


class KayitBulunamadiHatasi(KutuphaneHatasi):
    kod = 404


class StokYokHatasi(KutuphaneHatasi):
    kod = 409


class CakismaHatasi(KutuphaneHatasi):
    kod = 409
