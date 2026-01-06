# JOKER Pazaryeri - Trendyol Entegrasyonu

## Genel Bilgi

Trendyol'un REST API v2.0'ını kullanarak Odoo ile entegrasyon sağlayan modüldür.

## Özellikler

### Sipariş Senkronizasyonu (İki Yönlü)
- Trendyol'dan siparişleri otomatik olarak çek
- Siparişleri Odoo'da satış siparişine dönüştür
- Kargo bilgisini Trendyol'a gönder

### Stok Yönetimi (Bir Yönlü - Odoo → Trendyol)
- Odoo'daki stok değişikliklerini Trendyol'a senkronize et
- Eksik stok uyarıları

### Fiyat Yönetimi (Bir Yönlü - Odoo → Trendyol)
- Odoo'daki fiyat değişikliklerini Trendyol'a senkronize et
- Dinamik fiyatlandırma desteği

### Webhook Desteği
- Trendyol webhooks'larını al ve işle
- Sipariş oluşturma, durum değişikliği bildirimleri

## API Kimlik Bilgileri

Trendyol Developer Portal'dan:

1. **Merchant ID**: Satıcı ID'niz
2. **API Key**: API anahtar bilgisi
3. **API Secret**: API gizli anahtarı (API Key ile aynı olabilir)

## Kurulum

1. Modülü yükle
2. **Pazaryeri → Pazaryeri Kanalları**'ndan yeni kanal oluştur
3. Kanal tipi: "Trendyol"
4. API kimlik bilgilerini gir
5. "Bağlantıyı Test Et" butonu ile test et

## API Endpoints (Trendyol)

### Orders
```
GET /v2/merchant/{merchantId}/orders
GET /v2/merchant/{merchantId}/orders/{orderId}
PUT /v2/merchant/{merchantId}/orders/{orderId}/status
```

### Products
```
GET /v2/merchant/{merchantId}/products
GET /v2/merchant/{merchantId}/products/{productId}
PUT /v2/merchant/{merchantId}/products/{productId}
```

### Stock
```
PUT /v2/merchant/{merchantId}/products/{productId}/stock
```

### Price
```
PUT /v2/merchant/{merchantId}/products/{productId}/price
```

## Senkronizasyon Aralıkları

- **Siparişler**: Her 15-30 dakika
- **Stok**: Gerçek zamanlı (Odoo'da değişiklik yapıldığında)
- **Fiyat**: Saatlik

## Webhook Yapılandırması

Trendyol Developer Console'da webhook'u yapılandır:

```
URL: https://{your-domain}/api/webhook/marketplace/trendyol

Events:
- OrderCreated
- OrderStatusChanged
```

## Lisans

LGPL-3
