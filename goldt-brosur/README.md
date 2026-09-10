# Gold T® Mini — Kadın Doğum & IVF Hekim Broşürü

GoldLuna EXCLUSIVE hekim broşürünün (v3) **Gold T® Mini (Eurogine, S.L.)** sürümü.
Aynı tasarım dili, 16 sayfa, 960 × 540 pt (16:9).

## Dosyalar

| Dosya | Açıklama |
|---|---|
| `GoldT_Mini_Hekim_Brosuru_v1.pdf` | Basılabilir/sunulabilir broşür, 16 sayfa |
| `goldt.html` | Kaynak (tek dosya, mutlak konumlandırma) |
| `assets/` | Görseller (ürün, inserter, tel kesiti, yaşam tarzı) |
| `fonts/` | Plus Jakarta Sans woff2 (SIL Open Font License 1.1) |
| `build.sh` | Chromium ile PDF üretimi |

Yeniden üretmek için: `./build.sh` (Chromium yolu için `CHROME=` değişkeni).

## Sayfa planı

1. Kapak — Gold T® Mini kimliği
2. Ürün: nedir, iki yönlü etki, ürün görseli
3. Ürün: teknik künye + ürün kodları + belge farkı uyarısı
4. Ürün: iki boy (Mini 24 × 30,5 mm / Normal 31 × 33 mm), ölçekli şema
5. Teknoloji: altın çekirdek — gerekçe ve karşı hipotez
6. Teknoloji: yerleştirme sistemi, uygulama akışı
7. Hormonsuz etki + Skovlund grafiği
8. Klinik fark: CDC MEC 2024, Mørch, Liu
9. Kanıt: küçük çerçeve/nullipar (Hubacher, Akintomide 2022)
10. Kanıt: geometri ve ekspulsiyon (Boehnke, Akintomide 2021, Foran)
11. **Güvenlik: spontan kırılma (Semiz & Özbay 2025)**
12. **Güvenlik: 2018–19 saha güvenlik bildirimi (AEMPS/BfArM/FSRH)**
13. Kimler için: IVF arası dönem, acil kontrasepsiyon, emzirme, perimenopoz
14. Üretici ve kalite: Eurogine, ISO 13485, CE 0318, MDR Class III
15. Tedarik: ürün kodları, Türkiye durumu, kontrol listesi
16. Kapanış + kaynakça

## GoldLuna v3'ten farklar

**Ürün verisi baştan değişti**
- 380 mm² → **375 mm²** aktif bakır; 18 ayar altın halkalar → **0,1 mm altın çekirdekli bakır tel**
- Zambak çerçeve → **T/Y çerçeve**; boylar MINI 30,5 × 24 → **24 × 30,5 mm**, NORMAL 32 × 32 → **31 × 33 mm**
- Almanya üretimi → **İspanya, Castelldefels (Eurogine, S.L.)**
- Ürün kodları eklendi: ref. 01040200, GTIN 8436021830173, PZN 14057156, C.N. 337793.5

**Eklenen sayfalar**
- Teknik künye ve ürün kodları (s. 3)
- Altın çekirdek teknolojisi (s. 5)
- Yerleştirme sistemi (s. 6)
- Spontan kırılma yayını (s. 11)
- Saha güvenlik bildirimi (s. 12)
- Üretici ve kalite sistemi (s. 14)
- Tedarik ve Türkiye durumu (s. 15)
- Kaynakça (s. 16)

**Kaldırılan/düzeltilen iddialar**
- Altının antibakteriyel/şifa etkisi iddiası kaldırıldı — Eurogine altın için yalnızca mekanik/korozyon dayanımı bildiriyor
- Ürüne özel sonda cm eşikleri kaldırıldı; Gold T IFU'su boy başına sayısal eşik yayımlamıyor ("IFU'dan doğrulayın" uyarısı eklendi)
- 10 yıl (Medaks 2017 sayfası) değil **en çok 5 yıl** (üreticinin güncel belgeleri)
- Rev. 11/2020 föyündeki 375 vs 380 mm² tutarsızlığı açıkça işaretlendi

**Atıf düzeltmeleri (PubMed üzerinden doğrulandı)**
- Boehnke (Bohnke değil); kohort EURAS-LCS12
- Hubacher 2022: 927 randomize / 908 analiz; cihaz NT380-Mini
- Huang 2026 künyesi tamamlandı: Front Cell Dev Biol. 2026;14:1790194
- Turok 2021: "Nourse" yazarı kaldırıldı; bakır kolunda n=321, 0 gebelik
- EURAS-IUD Pearl 0,52: 58.324 kişilik kohort **tüm RİA** kohortudur, bakır alt grubu değil
- ACOG "birinci basamak" ifadesi güncel değil → Practice Bulletin 186 (2017) / Committee Statement No. 5 (2023) ifadesi
- Mørch 2024 araştırma mektubu; HR 1,4 (1,2–1,5)

## Doğrulanması gerekenler (tedarik öncesi)

- Türkiye distribütörlüğü/ithalat yetkisi — Medaks Sağlık sayfası 2017 tarihli ve güncel değil; TİTCK ÜTS kaydı sorgulanmalı
- ISO 13485 sertifikasının (2012 01 0006 EN) 26 Kasım 2026 sonrası yenilenme durumu
- Gold T IFU'sunda boy başına kavite uzunluğu eşiği ve acil kontrasepsiyon endikasyonu

## Notlar

- Görseller temsilîdir; ürün fotoğrafı, inserter ve tel kesiti görselleri üretilmiştir, üreticinin resmi ürün fotoğrafları değildir.
- Doküman hekime yönelik bilimsel bilgilendirme amaçlıdır; hasta tanıtım materyali değildir.

---

# v2 — güncel sürüm (12 sayfa)

`GoldT_Mini_Hekim_Brosuru_v2.pdf` · kaynak `goldt_v2.html` · `./build.sh goldt_v2.html`

v1'de üstünlükler ve karşılaştırmalar dört sayfaya yayılmıştı. v2 bunları **iki sayfada** toplar ve
altın çekirdeğe **kendi sayfasını** verir. Sayfa sayısı 16 → 12.

## v2 sayfa planı

| # | Sayfa |
|---|---|
| 01 | Kapak |
| 02 | Gold T Mini nedir — mekanizma, ürün görseli |
| 03 | Teknik künye ve ürün kodları |
| 04 | İki boy — Mini / Normal, ölçekli şema |
| 05 | **Neden altın çekirdek?** (yeni, tek sayfa) |
| 06 | Yerleştirme sistemi |
| 07 | **Alternatif yöntemlere karşı** — LNG-RİS, deri altı implant, kombine hap |
| 08 | **RİA'lar arasında nerede duruyor?** — şekil (Ballerine dâhil), genişlik, bakır yükü |
| 09 | Güvenlik profili — spontan kırılma + saha güvenlik bildirimi (birleştirildi) |
| 10 | Kimler için — IVF arası dönem, acil kontrasepsiyon, emzirme, perimenopoz |
| 11 | Üretici, kalite ve tedarik (birleştirildi) |
| 12 | Kapanış + kaynakça |

## v1 → v2 değişiklikleri

**Birleştirildi (4 sayfa → 2)**
- v1'in hormonsuz etki (s.07), klinik fark (s.08), MINI kanıtı (s.09) ve geometri (s.10) sayfaları,
  v2'de s.07 (yöntem karşılaştırması) ve s.08 (cihaz karşılaştırması) olarak toplandı.
- Güvenlik s.11 + s.12 → tek sayfa (s.09). Üretici s.14 + tedarik s.15 → tek sayfa (s.11).

**Yeni sayfa 05 — Neden altın çekirdek?**
- Sorun: kontraseptif etki bakırın korozyonuyla oluşur; tel beş yıl boyunca aşınır ve kırılganlaşır.
  Bakır telin ikincil fragmentasyonu literatürde bildirilmiştir (Dubovis & Rizk 2020).
- Emsal: **Nova-T 380'in 0,4 mm bakır telinde 0,1 mm gümüş çekirdek** vardır ve üretici bu çekirdeğin
  işlevini korozyona bağlı fragmentasyonu önlemek olarak tanımlar. Gold T aynı mimariyi altınla kurar.
- Altının uygunluğu: soy metal, biyouyumlu, sünek, mekanik süreklilik.
- Sınırlar: altın kontraseptif etki üretmez; üretici antibakteriyel/tedavi edici iddia bildirmez;
  "ayar"/"altın halka" benzetmeleri bu ürüne uymaz (tek bir 0,1 mm çekirdek).
- Gerçek tel kesiti makro görseli ve ölçekli korozyon şeması.

**Yeni sayfa 07 — yöntem karşılaştırması**
11 satırlık tablo: hormon, süre, başarısızlık, kullanıcı hatası, uygulama, adet paterni,
US MEC kategorileri (meme kanseri / VTE / auralı migren), emzirme, bırakma nedeni, doğurganlığa dönüş.
Yanında üç kanıt kutusu — Mørch 2024, Liu 2024 ve üç yöntemi doğrudan karşılaştıran Modesto 2014
(bakırlı RİA'nın devam oranı en düşük: %73,2 — dürüst karşılaştırma).

**Yeni sayfa 08 — cihaz karşılaştırması**
- Dört çerçeve geometrisinin ölçekli şeması ve Boehnke 2024 ekspulsiyon aHR'leri:
  T/Y 1,0× (referans) · çerçevesiz 1,3× · kanatlı 1,6× · **küresel 3,6×**.
- Ballerine için çelişkili veri açıkça verildi: bağımsız prospektif çalışmada 12 ayda ekspulsiyon
  **%27 (14/51)** (Wiebe & Trussell 2015), üretici bağlantılı gerçek yaşam çalışmalarında %3,4–5,3.
- Bakır yükü: Cochrane derlemesi yüksek bakır yüklü cihazların üstünlüğünü gösterir; aynı derleme
  nullipar kadınlar için hiçbir çerçeveli cihazın üstün olmadığını da belirtir.

**Eklenen kaynaklar (PubMed üzerinden doğrulandı)**
Kulier 2007 (Cochrane CD005347) · Wiebe & Trussell 2015 · Baram 2019 · Yaron 2019 ·
Modesto 2014 · Jensen 2022 (Mirena Extension Trial) · Dubovis & Rizk 2020 · Batár 2002 (Nova-T 380) ·
Gaio 2024 (acil kontrasepsiyon meta-analizi) · Bayer Nova-T 380 ürün bilgisi.
