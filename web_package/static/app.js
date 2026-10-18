/* Üniversite Online Kütüphane - web arayüzü (Vanilla JS ve Fetch API) */
'use strict';

// yardımcılar
const $ = (s, r = document) => r.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const tl = (n) => new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY' }).format(n || 0);
const tarih = (d) => (d ? new Date(d + 'T00:00:00').toLocaleDateString('tr-TR') : '—');
const debounce = (fn, ms = 250) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };

const IKON = {
  chart: '<path stroke-linecap="round" stroke-linejoin="round" d="M3 3v18h18M7 14l4-4 3 3 5-6"/>',
  book: '<path stroke-linecap="round" stroke-linejoin="round" d="M12 6.25v13m0-13C10.83 5.48 9.25 5 7.5 5S4.17 5.48 3 6.25v13C4.17 18.48 5.75 18 7.5 18s3.33.48 4.5 1.25m0-13C13.17 5.48 14.75 5 16.5 5c1.75 0 3.33.48 4.5 1.25v13C19.83 18.48 18.25 18 16.5 18c-1.75 0-3.33.48-4.5 1.25"/>',
  swap: '<path stroke-linecap="round" stroke-linejoin="round" d="M7 7h12m0 0-4-4m4 4-4 4M17 17H5m0 0 4-4m-4 4 4 4"/>',
  wallet: '<path stroke-linecap="round" stroke-linejoin="round" d="M3 7a2 2 0 0 1 2-2h13v4M3 7v10a2 2 0 0 0 2 2h14a1 1 0 0 0 1-1v-9a1 1 0 0 0-1-1H5a2 2 0 0 1-2-2zm13 6h.01"/>',
  alert: '<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v4m0 4h.01M10.3 3.9 2.4 18a2 2 0 0 0 1.7 3h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>',
  users: '<path stroke-linecap="round" stroke-linejoin="round" d="M17 20h5v-2a4 4 0 0 0-3-3.87M9 20H2v-2a4 4 0 0 1 4-4h2a4 4 0 0 1 4 4v2zm3-12a3 3 0 1 1-6 0 3 3 0 0 1 6 0zm7 2a3 3 0 1 1-4-2.83"/>',
  search: '<path stroke-linecap="round" stroke-linejoin="round" d="m21 21-4.3-4.3M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0z"/>',
  plus: '<path stroke-linecap="round" stroke-linejoin="round" d="M12 5v14M5 12h14"/>',
};
const ikon = (ad, cls = 'w-5 h-5') => `<svg class="${cls}" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">${IKON[ad]}</svg>`;

// API istemcisi
async function api(yol, { method = 'GET', body } = {}) {
  const r = await fetch('/api' + yol, {
    method,
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : {},
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  let veri = null;
  try { veri = await r.json(); } catch (_) { /* gövde yok */ }
  if (!r.ok) {
    let mesaj = 'Beklenmeyen bir hata oluştu.';
    if (veri && typeof veri.detail === 'string') mesaj = veri.detail;
    else if (veri && Array.isArray(veri.detail)) mesaj = veri.detail.map((d) => `${(d.loc || []).slice(1).join('.')}: ${d.msg}`).join(' • ');
    const e = new Error(mesaj); e.status = r.status; throw e;
  }
  return veri;
}

function toast(mesaj, tur = 'ok') {
  const simge = { ok: '✅', warn: '⚠️', err: '⛔' }[tur];
  const el = document.createElement('div');
  el.className = `toast ${tur}`;
  el.setAttribute('role', 'status');
  el.innerHTML = `<span>${simge}</span><span>${esc(mesaj)}</span>`;
  $('#toasts').appendChild(el);
  setTimeout(() => { el.classList.add('out'); setTimeout(() => el.remove(), 300); }, 4200);
}
const hataGoster = (e) => toast(e.message, e.status === 409 ? 'warn' : 'err');

// durum
const durum = {
  uyeler: [],
  aktif: null,
  sekme: null,
  oduncFiltre: 'aktif',
  secilenKitapId: null,
  borcUyeId: null,
  arama: '',
  kategori: '',
};

const yonetici = () => durum.aktif && durum.aktif.rol === 'Yonetici';

const SEKMELER = [
  { id: 'panel', ad: 'Panel', ikon: 'chart', roller: ['Yonetici'], alt: 'Kütüphanenin anlık durumu', goster: panelGoster },
  { id: 'kitaplar', ad: 'Kitaplar', ikon: 'book', roller: ['Yonetici', 'Ogrenci'], alt: 'Katalogda ara, filtrele ve yönet', goster: kitaplarGoster },
  { id: 'odunc', ad: 'Ödünç / İade', adOgrenci: 'Ödünçlerim', ikon: 'swap', roller: ['Yonetici', 'Ogrenci'], alt: 'Ödünç verme, iade alma ve gecikme simülasyonu', goster: oduncGoster },
  { id: 'borc', ad: 'Borç Ödeme', adOgrenci: 'Borçlarım', ikon: 'wallet', roller: ['Yonetici', 'Ogrenci'], alt: 'Gecikme cezalarını görüntüle ve öde', goster: borcGoster },
  { id: 'rapor', ad: 'Gecikme Raporu', ikon: 'alert', roller: ['Yonetici'], alt: 'Teslim tarihi geçmiş ve cezaya düşmüş işlemler', goster: raporGoster },
  { id: 'uyeler', ad: 'Üyeler', ikon: 'users', roller: ['Yonetici'], alt: 'Kayıtlı üyeler ve borç durumları', goster: uyelerGoster },
];
const izinliSekmeler = () => SEKMELER.filter((s) => s.roller.includes(durum.aktif.rol));

// iskelet
function menuCiz() {
  $('#menu').innerHTML = izinliSekmeler().map((s) => `
    <button class="nav-btn ${s.id === durum.sekme ? 'active' : ''}" data-eylem="sekme" data-id="${s.id}" id="nav-${s.id}">
      ${ikon(s.ikon)}<span>${yonetici() ? s.ad : (s.adOgrenci || s.ad)}</span>
    </button>`).join('');
}

function ustCiz() {
  const sec = $('#kullaniciSec');
  const grup = (rol, baslik) => `<optgroup label="${baslik}">${durum.uyeler.filter((u) => u.rol === rol)
    .map((u) => `<option value="${u.uyeId}" ${u.uyeId === durum.aktif.uyeId ? 'selected' : ''}>${esc(u.adSoyad)}</option>`).join('')}</optgroup>`;
  sec.innerHTML = grup('Yonetici', 'Yönetici') + grup('Ogrenci', 'Öğrenci');
  const b = durum.aktif.toplamBorc;
  $('#borcRozeti').innerHTML = `
    <span class="chip ${b > 0 ? 'chip-bad' : 'chip-ok'}" title="Aktif kullanıcının toplam borcu">
      ${yonetici() ? 'Yönetici' : 'Öğrenci'} • Borç: ${tl(b)}
    </span>`;
  const s = SEKMELER.find((x) => x.id === durum.sekme);
  $('#sayfaBaslik').textContent = s ? (yonetici() ? s.ad : (s.adOgrenci || s.ad)) : 'Kütüphane';
  $('#sayfaAlt').textContent = s ? s.alt : '';
}

const yukleniyor = () => { $('#icerik').innerHTML = '<div class="flex justify-center py-24"><div class="spinner"></div></div>'; };

async function sekmeGoster(id) {
  const izinli = izinliSekmeler();
  const s = izinli.find((x) => x.id === id) || izinli[0];
  durum.sekme = s.id;
  menuCiz(); ustCiz(); yukleniyor();
  try { await s.goster(); } catch (e) { $('#icerik').innerHTML = `<div class="glass p-8 text-center text-rose-300">${esc(e.message)}</div>`; }
}

async function uyeleriYenile() {
  durum.uyeler = await api('/uyeler');
  const guncel = durum.uyeler.find((u) => u.uyeId === (durum.aktif && durum.aktif.uyeId));
  if (guncel) durum.aktif = guncel;
}

async function yenile() { await uyeleriYenile(); await sekmeGoster(durum.sekme); }

const bos = (mesaj) => `<div class="p-10 text-center text-slate-400">${esc(mesaj)}</div>`;

// Panel (yönetici)
async function panelGoster() {
  const [o, rapor] = await Promise.all([api('/ozet'), api('/rapor/gecikme')]);
  const kart = (baslik, deger, renk, alt) => `
    <div class="glass p-5 relative overflow-hidden hover-lift fade-up">
      <div class="stat-glow" style="background:${renk}"></div>
      <p class="text-xs uppercase tracking-wider text-slate-400 font-semibold">${baslik}</p>
      <p class="font-display text-3xl font-bold mt-2">${deger}</p>
      <p class="text-xs text-slate-500 mt-1">${alt}</p>
    </div>`;
  const geciken = rapor.satirlar.filter((s) => s.tur.startsWith('Geciken')).slice(0, 5);
  $('#icerik').innerHTML = `
    <div class="grid grid-cols-2 xl:grid-cols-3 gap-4">
      ${kart('Kitap Çeşidi', o.toplamKitapCesidi, '#7c5cff', `${o.toplamStok} adet rafta`)}
      ${kart('Aktif Ödünç', o.aktifOdunc, '#22d3ee', 'Teslim edilmeyi bekleyen')}
      ${kart('Geciken', o.gecikenOdunc, '#fb7185', 'Son teslim tarihi geçmiş')}
      ${kart('Üye Sayısı', o.toplamUye, '#34d399', 'Öğrenci ve yönetici')}
      ${kart('Toplam Borç', tl(o.toplamBorc), '#fbbf24', 'Ödenmemiş cezalar')}
      ${kart('Raftaki Stok', o.toplamStok, '#a78bfa', 'Ödünç verilebilir adet')}
    </div>
    <section class="glass mt-5 overflow-hidden fade-up">
      <div class="p-5 flex items-center justify-between">
        <h2 class="font-display text-lg font-semibold">Teslim Tarihi Geçmiş Kitaplar</h2>
        <button class="btn btn-sm" data-eylem="sekme" data-id="rapor">Tüm rapor →</button>
      </div>
      ${geciken.length ? `<div class="overflow-x-auto"><table class="tbl"><thead><tr><th>Üye</th><th>Kitap</th><th>Son Teslim</th><th>Gecikme</th><th>Tahmini Ceza</th></tr></thead><tbody>
        ${geciken.map((s) => `<tr><td class="font-medium">${esc(s.uyeAdSoyad)}</td><td>${esc(s.kitapBaslik)}</td><td>${tarih(s.sonTeslimTarihi)}</td>
        <td><span class="chip chip-bad">${s.gecikmeGunSayisi} gün</span></td><td class="font-semibold text-amber-300">${tl(s.tutar)}</td></tr>`).join('')}
      </tbody></table></div>` : bos('Geciken kitap yok 🎉')}
    </section>`;
}

// Kitaplar
function stokRozeti(n) {
  if (n <= 0) return '<span class="chip chip-bad">Stokta yok</span>';
  if (n === 1) return '<span class="chip chip-warn">Son 1 adet</span>';
  return `<span class="chip chip-ok">${n} adet</span>`;
}

async function kitaplarGoster() {
  const kategoriler = await api('/kategoriler');
  $('#icerik').innerHTML = `
    <div class="glass p-4 mb-5 flex flex-wrap gap-3 items-end fade-up">
      <div class="flex-1 min-w-[220px]">
        <label class="lbl" for="aramaKutusu">Kitap Ara</label>
        <div class="relative">
          <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">${ikon('search', 'w-4 h-4')}</span>
          <input id="aramaKutusu" class="input pl-10" placeholder="Başlık, yazar, kategori veya ISBN…" value="${esc(durum.arama)}" />
        </div>
      </div>
      <div class="min-w-[180px]">
        <label class="lbl" for="kategoriSec">Kategori</label>
        <select id="kategoriSec" class="input">
          <option value="">Tümü</option>
          ${kategoriler.map((k) => `<option ${k === durum.kategori ? 'selected' : ''}>${esc(k)}</option>`).join('')}
        </select>
      </div>
      ${yonetici() ? `<button id="yeniKitapBtn" class="btn btn-primary" data-eylem="kitapForm">${ikon('plus', 'w-4 h-4')} Yeni Kitap</button>` : ''}
    </div>
    <div id="kitapListe"></div>`;
  const listele = async () => {
    const qs = new URLSearchParams();
    if (durum.arama) qs.set('arama', durum.arama);
    if (durum.kategori) qs.set('kategori', durum.kategori);
    const kitaplar = await api('/kitaplar?' + qs);
    $('#kitapListe').innerHTML = kitaplar.length ? `<div class="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">${kitaplar.map(kitapKarti).join('')}</div>`
      : `<div class="glass">${bos('Aramanızla eşleşen kitap bulunamadı.')}</div>`;
  };
  $('#aramaKutusu').addEventListener('input', debounce((e) => { durum.arama = e.target.value.trim(); listele().catch(hataGoster); }));
  $('#kategoriSec').addEventListener('change', (e) => { durum.kategori = e.target.value; listele().catch(hataGoster); });
  await listele();
}

function kitapKarti(k, i) {
  const eylem = yonetici()
    ? `<button class="btn btn-sm" data-eylem="kitapForm" data-id="${k.kitapId}">Düzenle</button>
       <button class="btn btn-sm btn-primary" data-eylem="oduncVerGit" data-id="${k.kitapId}">Ödünç Ver</button>`
    : `<button class="btn btn-sm btn-primary" data-eylem="oduncAl" data-id="${k.kitapId}">Ödünç Al</button>`;
  return `
    <article class="glass p-5 hover-lift fade-up flex flex-col gap-3" style="animation-delay:${Math.min(i, 8) * 40}ms" id="kitap-${k.kitapId}">
      <div class="flex items-start justify-between gap-3">
        <span class="chip chip-brand">${esc(k.kategori)}</span>${stokRozeti(k.stokAdedi)}
      </div>
      <div class="flex-1">
        <h3 class="font-display text-lg font-semibold leading-snug">${esc(k.baslik)}</h3>
        <p class="text-sm text-slate-400 mt-1">${esc(k.yazar)}</p>
        <p class="text-xs text-slate-500 mt-2 font-mono">ISBN ${esc(k.isbn)}</p>
      </div>
      <div class="flex gap-2 justify-end pt-1">${eylem}</div>
    </article>`;
}

async function kitapFormAc(id) {
  const k = id ? await api('/kitaplar/' + id) : { isbn: '', baslik: '', yazar: '', kategori: '', stokAdedi: 1 };
  const alan = (ad, etiket, tur = 'text', ekstra = '') => `
    <div><label class="lbl" for="f-${ad}">${etiket}</label>
    <input class="input" id="f-${ad}" name="${ad}" type="${tur}" value="${esc(k[ad])}" required ${ekstra}/></div>`;
  modalAc(`
    <h2 class="font-display text-xl font-bold mb-4">${id ? 'Kitabı Güncelle' : 'Yeni Kitap Ekle'}</h2>
    <form data-form="kitap" data-id="${id || ''}" class="grid gap-4">
      ${alan('baslik', 'Başlık')}${alan('yazar', 'Yazar')}
      <div class="grid grid-cols-2 gap-4">${alan('kategori', 'Kategori')}${alan('stokAdedi', 'Stok Adedi', 'number', 'min="0"')}</div>
      ${alan('isbn', 'ISBN')}
      <div class="flex justify-end gap-2 pt-2">
        <button type="button" class="btn" data-eylem="modalKapat">Vazgeç</button>
        <button type="submit" class="btn btn-primary" id="kitapKaydet">${id ? 'Güncelle' : 'Kitabı Ekle'}</button>
      </div>
    </form>`);
}

// Ödünç / İade
function oduncDurumu(o) {
  if (o.aktifMi && o.gecikmisMi) return `<span class="chip chip-bad">${o.gecikmeGunSayisi} gün gecikmiş</span>`;
  if (o.aktifMi) return '<span class="chip chip-info">Ödünçte</span>';
  if (o.gecikmeGunSayisi > 0) return `<span class="chip chip-warn">Gecikmeli iade (${o.gecikmeGunSayisi} gün)</span>`;
  return '<span class="chip chip-ok">Zamanında iade</span>';
}

async function oduncGoster() {
  const adm = yonetici();
  let form = '';
  if (adm) {
    const kitaplar = await api('/kitaplar');
    const ogrenciler = durum.uyeler.filter((u) => u.rol === 'Ogrenci');
    form = `
      <form data-form="odunc" class="glass p-5 mb-5 grid md:grid-cols-[1fr_1.4fr_120px_auto] gap-4 items-end fade-up">
        <div><label class="lbl" for="oduncUye">Öğrenci</label>
          <select id="oduncUye" name="uyeId" class="input" required>
            ${ogrenciler.map((u) => `<option value="${u.uyeId}">${esc(u.adSoyad)} (${esc(u.ogrenciNo)})</option>`).join('')}
          </select></div>
        <div><label class="lbl" for="oduncKitap">Kitap</label>
          <select id="oduncKitap" name="kitapId" class="input" required>
            ${kitaplar.map((k) => `<option value="${k.kitapId}" ${k.kitapId === durum.secilenKitapId ? 'selected' : ''}>${esc(k.baslik)} — stok: ${k.stokAdedi}</option>`).join('')}
          </select></div>
        <div><label class="lbl" for="oduncGun">Süre (gün)</label>
          <input id="oduncGun" name="gunSayisi" type="number" min="1" max="90" value="14" class="input" /></div>
        <button class="btn btn-primary h-[42px]" type="submit" id="oduncVerBtn">Ödünç Ver</button>
      </form>`;
    durum.secilenKitapId = null;
  }
  const qs = new URLSearchParams();
  if (!adm) qs.set('uyeId', durum.aktif.uyeId);
  let liste = await api('/odunc?' + qs);
  const filtreler = [['aktif', 'Aktif'], ['geciken', 'Geciken'], ['tumu', 'Tümü']];
  if (durum.oduncFiltre === 'aktif') liste = liste.filter((o) => o.aktifMi);
  if (durum.oduncFiltre === 'geciken') liste = liste.filter((o) => o.aktifMi && o.gecikmisMi);

  const satir = (o) => `
    <tr id="odunc-${o.oduncId}">
      ${adm ? `<td class="font-medium">${esc(o.uyeAdSoyad)}</td>` : ''}
      <td>${esc(o.kitapBaslik)}</td><td>${tarih(o.alisTarihi)}</td><td>${tarih(o.sonTeslimTarihi)}</td><td>${tarih(o.iadeTarihi)}</td>
      <td>${oduncDurumu(o)}${o.aktifMi && o.tahminiCeza > 0 ? `<div class="text-xs text-amber-300 mt-1">Tahmini ceza: ${tl(o.tahminiCeza)}</div>` : ''}</td>
      <td>${o.aktifMi ? `<div class="flex gap-2 justify-end">
        <button class="btn btn-sm btn-ok" data-eylem="iade" data-id="${o.oduncId}">İade Al</button>
        <button class="btn btn-sm btn-warn" data-eylem="iade" data-id="${o.oduncId}" data-sim="5" title="Son teslim tarihinden 5 gün sonra iade edilmiş gibi işlem yapar">5 Gün Gecikmeli İade Et</button>
      </div>` : '<span class="text-slate-500 text-xs">—</span>'}</td>
    </tr>`;

  $('#icerik').innerHTML = `${form}
    <section class="glass overflow-hidden fade-up">
      <div class="p-4 flex flex-wrap gap-2 items-center justify-between">
        <h2 class="font-display text-lg font-semibold">${adm ? 'Ödünç Kayıtları' : 'Ödünç Aldığım Kitaplar'}</h2>
        <div class="flex gap-2">${filtreler.map(([id, ad]) => `<button class="btn btn-sm ${durum.oduncFiltre === id ? 'btn-primary' : ''}" data-eylem="oduncFiltre" data-id="${id}">${ad}</button>`).join('')}</div>
      </div>
      ${liste.length ? `<div class="overflow-x-auto"><table class="tbl" id="oduncTablo"><thead><tr>
        ${adm ? '<th>Üye</th>' : ''}<th>Kitap</th><th>Alış</th><th>Son Teslim</th><th>İade</th><th>Durum</th><th class="text-right">İşlem</th></tr></thead>
        <tbody>${liste.map(satir).join('')}</tbody></table></div>` : bos('Gösterilecek ödünç kaydı yok.')}
    </section>`;
}

// Borç Ödeme
async function borcGoster() {
  const adm = yonetici();
  if (adm && !durum.uyeler.some((u) => u.uyeId === durum.borcUyeId)) {
    const borclu = durum.uyeler.find((u) => u.rol === 'Ogrenci' && u.toplamBorc > 0) || durum.uyeler.find((u) => u.rol === 'Ogrenci');
    durum.borcUyeId = borclu ? borclu.uyeId : null;
  }
  const uyeId = adm ? durum.borcUyeId : durum.aktif.uyeId;
  const uye = await api('/uyeler/' + uyeId);
  const cezalar = await api('/cezalar?uyeId=' + uyeId);
  const secici = adm ? `
    <div class="glass p-4 mb-5 fade-up max-w-md"><label class="lbl" for="borcUye">Üye Seç</label>
      <select id="borcUye" class="input">
        ${durum.uyeler.filter((u) => u.rol === 'Ogrenci').map((u) => `<option value="${u.uyeId}" ${u.uyeId === uyeId ? 'selected' : ''}>${esc(u.adSoyad)} — ${tl(u.toplamBorc)}</option>`).join('')}
      </select></div>` : '';
  $('#icerik').innerHTML = `${secici}
    <div class="grid lg:grid-cols-[320px_1fr] gap-5">
      <div class="glass p-6 fade-up relative overflow-hidden self-start">
        <div class="stat-glow" style="background:${uye.toplamBorc > 0 ? '#fb7185' : '#34d399'}"></div>
        <p class="text-xs uppercase tracking-wider text-slate-400 font-semibold">${esc(uye.adSoyad)}</p>
        <p class="text-xs text-slate-500">${esc(uye.ogrenciNo)}</p>
        <p class="text-xs uppercase tracking-wider text-slate-400 font-semibold mt-5">Toplam Borç</p>
        <p id="toplamBorcDeger" class="font-display text-4xl font-bold mt-1 ${uye.toplamBorc > 0 ? 'text-rose-300' : 'text-emerald-300'}">${tl(uye.toplamBorc)}</p>
        <button class="btn btn-ok w-full mt-6" id="tumBorcBtn" data-eylem="borcTumu" data-id="${uye.uyeId}" ${uye.toplamBorc > 0 ? '' : 'disabled'}>Tüm Borcu Öde</button>
        <p class="text-xs text-slate-500 mt-3">Ödeme, açık ceza kayıtlarını kapatır ve toplam borcu sıfırlar.</p>
      </div>
      <section class="glass overflow-hidden fade-up">
        <div class="p-4"><h2 class="font-display text-lg font-semibold">Ceza Kayıtları</h2></div>
        ${cezalar.length ? `<div class="overflow-x-auto"><table class="tbl" id="cezaTablo"><thead><tr><th>Kitap</th><th>Gecikme</th><th>Tutar</th><th>Durum</th><th class="text-right">İşlem</th></tr></thead><tbody>
          ${cezalar.map((c) => `<tr id="ceza-${c.cezaId}"><td>${esc(c.kitapBaslik)}</td><td>${c.gecikmeGunSayisi} gün</td>
            <td class="font-semibold ${c.odendiMi ? 'text-slate-400' : 'text-amber-300'}">${tl(c.tutar)}</td>
            <td>${c.odendiMi ? `<span class="chip chip-ok">Ödendi • ${tarih(c.odemeTarihi)}</span>` : '<span class="chip chip-bad">Ödenmedi</span>'}</td>
            <td class="text-right">${c.odendiMi ? '' : `<button class="btn btn-sm btn-ok" data-eylem="cezaOde" data-id="${c.cezaId}">Öde</button>`}</td></tr>`).join('')}
        </tbody></table></div>` : bos('Bu üyeye ait ceza kaydı yok.')}
      </section>
    </div>`;
  const sec = $('#borcUye');
  if (sec) sec.addEventListener('change', (e) => { durum.borcUyeId = Number(e.target.value); sekmeGoster('borc'); });
}

// Gecikme Raporu
async function raporGoster() {
  const r = await api('/rapor/gecikme');
  const mini = (b, d, c) => `<div class="glass p-5 hover-lift fade-up"><p class="text-xs uppercase tracking-wider text-slate-400 font-semibold">${b}</p><p class="font-display text-3xl font-bold mt-2 ${c}">${d}</p></div>`;
  const rozet = (d) => ({ 'Teslim Edilmedi': 'chip-bad', 'Ceza Ödenmedi': 'chip-warn', 'Ceza Ödendi': 'chip-ok' }[d]);
  $('#icerik').innerHTML = `
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-5">
      ${mini('Geciken (Teslim Edilmedi)', r.gecikenAktifSayisi, 'text-rose-300')}
      ${mini('Cezalı Kayıt', r.cezaliKayitSayisi, 'text-amber-300')}
      ${mini('Toplam Ceza', tl(r.toplamCeza), '')}
      ${mini('Ödenmemiş Ceza', tl(r.odenmemisCeza), 'text-rose-300')}
    </div>
    <section class="glass overflow-hidden fade-up">
      ${r.satirlar.length ? `<div class="overflow-x-auto"><table class="tbl" id="raporTablo"><thead><tr><th>Tür</th><th>Üye</th><th>Kitap</th><th>Son Teslim</th><th>İade</th><th>Gecikme</th><th>Tutar</th><th>Durum</th></tr></thead><tbody>
        ${r.satirlar.map((s) => `<tr><td class="text-xs text-slate-400">${esc(s.tur)}</td><td class="font-medium">${esc(s.uyeAdSoyad)}</td><td>${esc(s.kitapBaslik)}</td>
          <td>${tarih(s.sonTeslimTarihi)}</td><td>${tarih(s.iadeTarihi)}</td><td><span class="chip chip-bad">${s.gecikmeGunSayisi} gün</span></td>
          <td class="font-semibold text-amber-300">${tl(s.tutar)}</td><td><span class="chip ${rozet(s.durum)}">${esc(s.durum)}</span></td></tr>`).join('')}
      </tbody></table></div>` : bos('Gecikme veya ceza kaydı yok.')}
    </section>`;
}

// Üyeler
async function uyelerGoster() {
  const uyeler = durum.uyeler;
  $('#icerik').innerHTML = `
    <div class="flex justify-end mb-4"><button class="btn btn-primary" data-eylem="uyeForm">${ikon('plus', 'w-4 h-4')} Yeni Üye</button></div>
    <section class="glass overflow-hidden fade-up"><div class="overflow-x-auto"><table class="tbl" id="uyeTablo"><thead><tr><th>#</th><th>Ad Soyad</th><th>No</th><th>E-posta</th><th>Rol</th><th>Toplam Borç</th></tr></thead><tbody>
      ${uyeler.map((u) => `<tr><td class="text-slate-500">${u.uyeId}</td><td class="font-medium">${esc(u.adSoyad)}</td><td class="font-mono text-xs">${esc(u.ogrenciNo)}</td><td class="text-slate-400">${esc(u.email)}</td>
        <td><span class="chip ${u.rol === 'Yonetici' ? 'chip-brand' : 'chip-info'}">${u.rol === 'Yonetici' ? 'Yönetici' : 'Öğrenci'}</span></td>
        <td class="font-semibold ${u.toplamBorc > 0 ? 'text-rose-300' : 'text-emerald-300'}">${tl(u.toplamBorc)}</td></tr>`).join('')}
    </tbody></table></div></section>`;
}

function uyeFormAc() {
  const alan = (ad, etiket, tur = 'text') => `<div><label class="lbl" for="u-${ad}">${etiket}</label><input class="input" id="u-${ad}" name="${ad}" type="${tur}" required /></div>`;
  modalAc(`
    <h2 class="font-display text-xl font-bold mb-4">Yeni Üye</h2>
    <form data-form="uye" class="grid gap-4">
      ${alan('adSoyad', 'Ad Soyad')}${alan('ogrenciNo', 'Öğrenci / Personel No')}${alan('email', 'E-posta', 'email')}
      <div><label class="lbl" for="u-rol">Rol</label><select class="input" id="u-rol" name="rol"><option value="Ogrenci">Öğrenci</option><option value="Yonetici">Yönetici</option></select></div>
      <div class="flex justify-end gap-2 pt-2"><button type="button" class="btn" data-eylem="modalKapat">Vazgeç</button><button class="btn btn-primary" type="submit">Kaydet</button></div>
    </form>`);
}

// modal
function modalAc(html) {
  $('#modalKok').innerHTML = `<div class="modal-bg" data-eylem="modalArka"><div class="glass modal" role="dialog" aria-modal="true">${html}</div></div>`;
  const ilk = $('#modalKok input, #modalKok select'); if (ilk) ilk.focus();
}
const modalKapat = () => { $('#modalKok').innerHTML = ''; };

// eylemler
const eylemler = {
  sekme: (d) => sekmeGoster(d.id),
  modalKapat,
  modalArka: (_, el, ev) => { if (ev.target === el) modalKapat(); },
  kitapForm: (d) => kitapFormAc(d.id).catch(hataGoster),
  uyeForm: uyeFormAc,
  oduncVerGit: (d) => { durum.secilenKitapId = Number(d.id); sekmeGoster('odunc'); },
  oduncFiltre: (d) => { durum.oduncFiltre = d.id; sekmeGoster('odunc'); },

  async oduncAl(d) {
    try {
      const o = await api('/odunc', { method: 'POST', body: { uyeId: durum.aktif.uyeId, kitapId: Number(d.id) } });
      toast(`'${o.kitapBaslik}' ödünç alındı. Son teslim: ${tarih(o.sonTeslimTarihi)}`);
      await yenile();
    } catch (e) { hataGoster(e); }
  },

  async iade(d) {
    try {
      const sim = Number(d.sim || 0);
      const s = await api(`/odunc/${d.id}/iade${sim ? '?simulasyon_gun=' + sim : ''}`, { method: 'POST' });
      toast(s.mesaj, s.ceza ? 'warn' : 'ok');
      await yenile();
    } catch (e) { hataGoster(e); }
  },

  async borcTumu(d) {
    try {
      const s = await api(`/uyeler/${d.id}/borc-ode`, { method: 'POST', body: {} });
      toast(s.mesaj); await yenile();
    } catch (e) { hataGoster(e); }
  },

  async cezaOde(d) {
    try {
      const s = await api(`/cezalar/${d.id}/ode`, { method: 'POST' });
      toast(s.mesaj); await yenile();
    } catch (e) { hataGoster(e); }
  },
};

document.addEventListener('click', (ev) => {
  const el = ev.target.closest('[data-eylem]');
  if (!el) return;
  const f = eylemler[el.dataset.eylem];
  if (f) f(el.dataset, el, ev);
});

document.addEventListener('submit', async (ev) => {
  const form = ev.target.closest('form[data-form]');
  if (!form) return;
  ev.preventDefault();
  const v = Object.fromEntries(new FormData(form));
  try {
    if (form.dataset.form === 'kitap') {
      const id = form.dataset.id;
      const body = { isbn: v.isbn.trim(), baslik: v.baslik.trim(), yazar: v.yazar.trim(), kategori: v.kategori.trim(), stokAdedi: Number(v.stokAdedi) };
      await api(id ? '/kitaplar/' + id : '/kitaplar', { method: id ? 'PUT' : 'POST', body });
      toast(id ? 'Kitap güncellendi.' : 'Yeni kitap eklendi.');
      modalKapat(); await yenile();
    } else if (form.dataset.form === 'odunc') {
      const o = await api('/odunc', { method: 'POST', body: { uyeId: Number(v.uyeId), kitapId: Number(v.kitapId), gunSayisi: Number(v.gunSayisi || 14) } });
      toast(`'${o.kitapBaslik}' → ${o.uyeAdSoyad} adına ödünç verildi. Stok 1 düştü.`);
      await yenile();
    } else if (form.dataset.form === 'uye') {
      await api('/uyeler', { method: 'POST', body: { adSoyad: v.adSoyad.trim(), ogrenciNo: v.ogrenciNo.trim(), email: v.email.trim(), rol: v.rol } });
      toast('Üye eklendi.'); modalKapat(); await yenile();
    }
  } catch (e) { hataGoster(e); }
});

document.addEventListener('keydown', (e) => { if (e.key === 'Escape') modalKapat(); });

$('#kullaniciSec').addEventListener('change', async (e) => {
  durum.aktif = durum.uyeler.find((u) => u.uyeId === Number(e.target.value));
  localStorage.setItem('aktifUyeId', durum.aktif.uyeId);
  durum.arama = ''; durum.kategori = ''; durum.oduncFiltre = 'aktif';
  await sekmeGoster(izinliSekmeler().some((s) => s.id === durum.sekme) ? durum.sekme : null);
});

// başlat
(async function baslat() {
  try {
    await uyeleriYenile();
    const kayitli = Number(localStorage.getItem('aktifUyeId'));
    durum.aktif = durum.uyeler.find((u) => u.uyeId === kayitli) || durum.uyeler.find((u) => u.rol === 'Yonetici') || durum.uyeler[0];
    await sekmeGoster(null);
  } catch (e) {
    $('#icerik').innerHTML = `<div class="glass p-8 text-center text-rose-300">Sunucuya bağlanılamadı: ${esc(e.message)}</div>`;
  }
})();
