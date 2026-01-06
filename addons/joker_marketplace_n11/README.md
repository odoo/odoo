# JOKER Pazaryeri - N11 Entegrasyonu

## Genel Bilgi

N11'nin SOAP/REST hybrid API'sini kullanarak Odoo ile entegrasyon sağlayan modüldür.

N11 API yapısı diğer pazaryerlerinden farklı olduğu için:
- **SOAP (Primary):** GetOrders, SetProductInventory, SetProductPrice vb.
- **REST (Secondary):** Bazı operasyonlar için fallback

## Özellikler

### Sipariş Senkronizasyonu (İki Yönlü)
- N11'den siparişleri otomatik olarak çek (SOAP)
- Siparişleri Odoo'da satış siparişine dönüştür
- Kargo bilgisini N11'ye gönder

### Stok Yönetimi (Bir Yönlü - Odoo → N11)
- Odoo'daki stok değişikliklerini N11'ye senkronize et (SOAP)
- Batch update desteği

### Fiyat Yönetimi (Bir Yönlü - Odoo → N11)
- Odoo'daki fiyat değişikliklerini N11'ye senkronize et (SOAP)

### Webhook Desteği
- N11 webhooks'larını al ve işle
- Sipariş oluşturma, durum değişikliği bildirimleri

## API Kimlik Bilgileri

N11 Developer Portal'dan:

1. **Merchant ID / Seller ID**: Satıcı ID'niz
2. **API Key**: API anahtar bilgisi
3. **API Secret**: API gizli anahtarı (REST requests için signing)

## WSDL Endpoints

```
SOAP: https://soap.n11.com/gateway/slave/RssFeedService
REST: https://api.n11.com/v1
```

## Kurulum

1. Modülü yükle
2. **Pazaryeri → Pazaryeri Kanalları**'ndan yeni kanal oluştur
3. Kanal tipi: "N11"
4. API kimlik bilgilerini gir
5. "Bağlantıyı Test Et" butonu ile test et

## SOAP Services (Önemli)

### GetOrders
```xml
<soap:Envelope>
  <authentication>
    <userName>MERCHANT_ID</userName>
    <userPassword>API_KEY</userPassword>
  </authentication>
  <pagingData>
    <pageNumber>1</pageNumber>
    <pageSize>100</pageSize>
  </pagingData>
  <orderFilter>
    <startDate>2026-01-01T00:00:00</startDate>
  </orderFilter>
</soap:Envelope>
```

### SetProductInventory
```xml
<soap:Envelope>
  <authentication>
    <userName>MERCHANT_ID</userName>
    <userPassword>API_KEY</userPassword>
  </authentication>
  <product>
    <productId>12345</productId>
    <inventory>100</inventory>
  </product>
</soap:Envelope>
```

### SetProductPrice
```xml
<soap:Envelope>
  <authentication>
    <userName>MERCHANT_ID</userName>
    <userPassword>API_KEY</userPassword>
  </authentication>
  <product>
    <productId>12345</productId>
    <price>99.99</price>
  </product>
</soap:Envelope>
```

## Senkronizasyon Aralıkları

- **Siparişler**: Her 30-60 dakika
- **Stok**: Gerçek zamanlı (Odoo'da değişiklik yapıldığında)
- **Fiyat**: Saatlik

## Teknik Detaylar

### ZEEP Library
N11 SOAP API'si için **zeep** Python library'sini kullanıyoruz:

```python
from zeep import Client
client = Client(wsdl='https://soap.n11.com/gateway/slave/RssFeedService')
```

### Error Handling
- SOAP Fault handling
- REST API fallback
- Automatic retry logic

### Signature (REST API)
N11 REST API requests HMAC-SHA256 imzası gerektirir:

```python
signature = HMAC-SHA256(api_key + timestamp, api_secret)
```

## Bilinen Kısıtlamalar

1. **SOAP Response Parsing**
   - N11 SOAP responses karmaşık XML yapısındadır
   - Custom parsing gerekebilir

2. **Pagination**
   - SOAP `pageSize` maksimum 100
   - Multiple page requests gerekebilir

3. **Rate Limiting**
   - N11 API rate limiting'i dikkatli olması gerekir
   - Default: 1000 requests/hour

## Troubleshooting

### SOAP Connection Hatası
```
ERROR: SOAP client not initialized
```
→ WSDL endpoint'ine erişim kontrol et

### Authentication Hatası
```
SOAP Fault: Invalid credentials
```
→ Merchant ID ve API Key'i kontrol et

### Timeout Hatası
```
Connection timeout
```
→ Network bağlantısını kontrol et, timeout süresini artır

## Lisans

LGPL-3
