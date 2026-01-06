# BizimHesap Connector - Odoo 19

## 📋 Genel Bakış

BizimHesap ön muhasebe yazılımı ile Odoo 19 ERP sistemini entegre eden modül.

**Versiyon**: 1.0
**Yazar**: MobilSoft
**Kategori**: Muhasebe / Entegrasyon
**Lisans**: LGPL-3

---

## 🔌 API Mimarisi

BizimHesap B2B API **çift yönlü** çalışır:

### ⬇️ BizimHesap → Odoo (GET)
- ✅ **Cariler** (`/customers`, `/suppliers`)
- ✅ **Ürünler** (`/products`)
- ✅ **Depolar** (`/warehouses`)
- ✅ **Stok** (`/inventory/{depo-id}`)
- ✅ **Cari Ekstre** (`/abstract/{musteri-id}`)

### ⬆️ Odoo → BizimHesap (POST)
- ✅ **Faturalar** (`/addinvoice`)
- ✅ **Fatura İptal** (`/cancelinvoice`)

### ⚠️ Desteklenmeyen
- ❌ Fatura listesi çekme (GET `/invoices` endpoint'i yok)
- ❌ Ödeme listesi çekme (GET `/payments` endpoint'i yok)

---

## 🚀 Özellikler

### ✅ Senkronizasyon
1. **Cari Senkronizasyonu**
   - BizimHesap müşteri ve tedarikçilerini Odoo'ya aktarır
   - VKN/Telefon/E-posta ile akıllı eşleştirme
   - Şube tespiti ve otomatik oluşturma
   - Bakiye bilgilerini günceller

2. **Ürün Senkronizasyonu**
   - BizimHesap ürünlerini Odoo'ya aktarır
   - Barkod ile kesin eşleştirme
   - Varyant desteği (Odoo 19 uyumlu)
   - Stok bilgisi aktarımı

3. **Fatura Gönderme**
   - Odoo'daki onaylı faturaları BizimHesap'a gönderir
   - Müşteri/Ürün binding kontrolü
   - GUID ile takip
   - PDF link alma

### 📊 Binding Yönetimi
- `bizimhesap.partner.binding` - Cari eşleştirmesi
- `bizimhesap.product.binding` - Ürün eşleştirmesi
- `bizimhesap.invoice.binding` - Fatura eşleştirmesi
- `bizimhesap.payment.binding` - Ödeme eşleştirmesi (hazır, API desteği yok)

### 🔍 Senkronizasyon Logları
Her API isteği kaydedilir:
- İşlem tipi (GET/POST)
- Durum (success/error/warning)
- Oluşturulan/Güncellenen/Hatalı kayıt sayısı
- Detaylı hata mesajları

---

## ⚙️ Kurulum

### 1. Modülü Yükle
```bash
# Modülü kopyala
cp -r bizimhesap_connector /opt/odoo/addons/

# Modülü güncelle
odoo -d YourDB -u bizimhesap_connector
```

### 2. BizimHesap Backend Oluştur
**Muhasebe > Yapılandırma > BizimHesap > Backends**

Gerekli bilgiler:
- **API URL**: `https://bizimhesap.com/api/b2b`
- **API Key (Firm ID)**: BizimHesap'tan alınan tekil ID
- **Kullanıcı Adı**: (opsiyonel)
- **Şifre**: (opsiyonel)

### 3. Bağlantıyı Test Et
"🔗 Bağlantıyı Test Et" butonuna tıkla → Durum "Bağlı" olmalı

### 4. İlk Senkronizasyon
"🔄 Tümünü Senkronize Et" → Cariler ve Ürünler çekilir

---

## 🔧 Kullanım

### Cari Senkronizasyonu
```
👥 Carileri Çek → BizimHesap müşteri ve tedarikçilerini Odoo'ya aktarır
```
**Akıllı Eşleştirme:**
1. VKN/TCKN kontrolü → Kesin eşleşme
2. Telefon kontrolü → Kesin eşleşme
3. E-posta kontrolü → Kesin eşleşme
4. İsim benzerliği ≥%80 + farklı adres → Şube
5. İsim benzerliği ≥%50 → Güncelle
6. Eşleşme yok → Yeni oluştur

### Ürün Senkronizasyonu
```
📦 Ürünleri Çek → BizimHesap ürünlerini Odoo'ya aktarır
```
**Eşleştirme:**
1. Barkod kontrolü → Kesin eşleşme
2. Ürün kodu kontrolü → Varyant olarak ekle
3. Eşleşme yok → Yeni oluştur

### Fatura Gönderme
```
📤 Faturaları Gönder → Odoo'daki onaylı faturaları BizimHesap'a gönderir
```
**Gereksinimler:**
- Fatura durumu: "Onaylandı" (posted)
- Müşteri/Tedarikçi BizimHesap'ta kayıtlı olmalı
- Ürünler BizimHesap'ta kayıtlı olmalı (önerilen)

**İşlem Akışı:**
1. Odoo faturası seç
2. BizimHesap formatına dönüştür
3. POST `/addinvoice` ile gönder
4. GUID al ve binding oluştur
5. PDF link kaydet

---

## 📡 API Endpoint Referansı

### GET Endpoints (BizimHesap → Odoo)

#### `/customers`
Müşteri listesi
```json
{
  "resultCode": 1,
  "data": {
    "customers": [
      {
        "id": "GUID",
        "code": "C001",
        "title": "ABC Ltd. Şti.",
        "address": "İstanbul",
        "taxno": "1234567890",
        "phone": "5321234567",
        "balance": "1,234.56",
        "currency": "TL"
      }
    ]
  }
}
```

#### `/suppliers`
Tedarikçi listesi (customers ile aynı format)

#### `/products`
Ürün listesi
```json
{
  "resultCode": 1,
  "data": {
    "products": [
      {
        "id": "GUID",
        "code": "P001",
        "title": "Ürün Adı",
        "barcode": "8690123456789",
        "price": "100.00",
        "currency": "TL",
        "stock": "50"
      }
    ]
  }
}
```

### POST Endpoints (Odoo → BizimHesap)

#### `/addinvoice`
Fatura gönderme
```json
{
  "firmId": "API_KEY",
  "invoiceNo": "INV/2026/0001",
  "invoiceType": 3,
  "dates": {
    "invoiceDate": "2026-01-06T00:00:00.000+03:00",
    "dueDate": "2026-02-06T00:00:00.000+03:00"
  },
  "customer": {
    "customerId": "CUSTOMER_GUID",
    "title": "ABC Ltd. Şti.",
    "taxNo": "1234567890"
  },
  "amounts": {
    "currency": "TL",
    "gross": "1,000.00",
    "discount": "0.00",
    "net": "1,000.00",
    "tax": "200.00",
    "total": "1,200.00"
  },
  "details": [
    {
      "productId": "PRODUCT_GUID",
      "productName": "Ürün Adı",
      "taxRate": "20.00",
      "quantity": 10,
      "unitPrice": "100.00",
      "total": "1,200.00"
    }
  ]
}
```

**Response:**
```json
{
  "error": "",
  "guid": "INVOICE_GUID",
  "url": "https://bizimhesap.com/invoice/pdf/..."
}
```

---

## 🔒 Güvenlik

### API Kimlik Doğrulama
BizimHesap B2B API, **Key** ve **Token** header'larını kullanır:
```python
headers = {
    "Key": "YOUR_API_KEY",
    "Token": "YOUR_API_KEY",  # Aynı değer
    "Content-Type": "application/json"
}
```

### Veri Gizliliği
- API Key şifreli saklanır (password field)
- Token bilgileri readonly
- Sync logları kullanıcı bazlı

---

## 📊 Raporlar ve İzleme

### Senkronizasyon Logları
**Muhasebe > Yapılandırma > BizimHesap > Sync Logs**

Görüntülenen bilgiler:
- İşlem (GET /customers, POST /addinvoice, vb.)
- Durum (success, error, warning)
- Oluşturulan/Güncellenen/Hatalı kayıt
- Detaylı hata mesajı
- İstek/Cevap verileri

### Binding Görüntüleme
**Muhasebe > Yapılandırma > BizimHesap > Partner/Product/Invoice Bindings**

Her binding gösterir:
- Odoo kaydı
- BizimHesap external ID (GUID)
- Son senkronizasyon tarihi
- Senkronizasyon durumu
- Ham veri (external_data JSON)

---

## 🐛 Hata Ayıklama

### Bağlantı Sorunları
```
Hata: HTTP 401 Unauthorized
Çözüm: API Key'i kontrol edin
```

```
Hata: HTTP 404 Not Found
Çözüm: API URL doğru mu? (https://bizimhesap.com/api/b2b)
```

### Senkronizasyon Hataları
```
Hata: "Invalid field 'external_data'"
Çözüm: Module upgrade yapın → -u bizimhesap_connector
```

```
Hata: "404 for url: .../invoices"
Durum: Normal - BizimHesap API GET /invoices sağlamıyor
Çözüm: Sadece POST /addinvoice kullanın (fatura gönderme)
```

### Log Kontrolü
```bash
# Odoo logları
docker compose logs odoo --tail=100 | grep bizimhesap

# Database logları
psql -U odoo -d YourDB -c "SELECT * FROM bizimhesap_sync_log ORDER BY id DESC LIMIT 20;"
```

---

## 🔄 Otomatik Senkronizasyon

### Cron Job
**Ayarlar > Teknik > Automation > Scheduled Actions**

Varsayılan: 30 dakikada bir
```python
backend._cron_sync_all()
```

### Manuel Kontrol
Backend formunda:
- ☑️ Otomatik Senkronizasyon
- Aralık: 30 dakika (önerilen)

---

## 🎯 İpuçları ve En İyi Uygulamalar

### 1. İlk Kurulum
✅ Önce carileri sync edin
✅ Sonra ürünleri sync edin
✅ Son olarak fatura göndermeyi test edin

### 2. Veri Kalitesi
✅ BizimHesap'ta VKN/Barkod bilgilerini doldurun
✅ Duplicate kontrol için telefon/e-posta ekleyin
✅ Ürün kodlarını standartlaştırın

### 3. Performans
✅ Büyük veri için auto_sync interval'i artırın
✅ İlk sync'te tüm verileri manuel çekin
✅ Cron job'ı yoğun saatlerde disable edin

### 4. Bakım
✅ Sync logları düzenli silin (>1000 kayıt)
✅ Backend test connection haftalık yapın
✅ API Key değişiminde tüm binding'leri kontrol edin

---

## 📚 Teknik Mimari

### Model Yapısı
```
bizimhesap.backend
├── bizimhesap.binding (Abstract)
│   ├── bizimhesap.partner.binding
│   ├── bizimhesap.product.binding
│   ├── bizimhesap.invoice.binding
│   └── bizimhesap.payment.binding
└── bizimhesap.sync.log
```

### Database Schema
```sql
-- Backend
bizimhesap_backend (id, name, api_key, state, ...)

-- Bindings
bizimhesap_partner_binding (id, backend_id, odoo_id, external_id, sync_date, ...)
bizimhesap_product_binding (id, backend_id, odoo_id, external_id, sync_date, ...)
bizimhesap_invoice_binding (id, backend_id, odoo_id, external_id, sync_date, ...)
bizimhesap_payment_binding (id, backend_id, odoo_id, external_id, sync_date, ...)

-- Logs
bizimhesap_sync_log (id, backend_id, operation, status, message, ...)
```

### API Request Flow
```
User Action
    ↓
action_sync_partners()
    ↓
get_customers() → _api_request()
    ↓
_get_headers() → requests.get()
    ↓
_import_partner() → SYNC_PROTOCOLS.match_partner()
    ↓
Create/Update res.partner
    ↓
Create bizimhesap.partner.binding
    ↓
_create_log()
```

---

## 🆘 Destek

- **Dokümantasyon**: Bu README
- **API Referansı**: `BizimHesap_B2B_API.pdf`
- **Sync Protocols**: `/opt/joker_stack/brain/sync_protocols.py`
- **İletişim**: MobilSoft (info@mobilsoft.com)

---

## 📝 Değişiklik Geçmişi

### v1.0 (2026-01-06)
- ✅ BizimHesap B2B API entegrasyonu
- ✅ Cari/Ürün senkronizasyonu (GET)
- ✅ Fatura gönderme (POST)
- ✅ Akıllı eşleştirme protokolleri
- ✅ Binding yönetimi
- ✅ Senkronizasyon logları
- ✅ Odoo 19 uyumluluğu

---

## ⚖️ Lisans

LGPL-3 - Detaylar için LICENSE dosyasına bakın.

---

**Geliştirici**: MobilSoft
**Tarih**: 6 Ocak 2026
**Odoo Versiyonu**: 19.0
**BizimHesap API**: B2B v1.0
