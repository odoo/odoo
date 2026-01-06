# JOKER Pazaryeri - Çiçek Sepeti Entegrasyonu

## Genel Bilgi

Çiçek Sepeti'nin modern REST API'sini kullanarak Odoo ile entegrasyon sağlayan modüldür.

Çiçek Sepeti hediye pazaryeri olduğu için özel işlevleri vardır:
- Kart notu desteği
- Teslimat saati seçimi
- Özel ambalaj seçenekleri
- Tebrik kartı

## Özellikler

### Sipariş Senkronizasyonu (İki Yönlü)
- Çiçek Sepeti'den siparişleri otomatik olarak çek
- Siparişleri Odoo'da satış siparişine dönüştür
- Kargo bilgisini Çiçek Sepeti'ye gönder

### Stok Yönetimi (Bir Yönlü - Odoo → Çiçek Sepeti)
- Odoo'daki stok değişikliklerini Çiçek Sepeti'ye senkronize et
- Eksik stok uyarıları

### Fiyat Yönetimi (Bir Yönlü - Odoo → Çiçek Sepeti)
- Odoo'daki fiyat değişikliklerini Çiçek Sepeti'ye senkronize et
- Dinamik fiyatlandırma desteği

### Webhook Desteği
- Çiçek Sepeti webhooks'larını al ve işle
- Sipariş oluşturma, durum değişikliği bildirimleri

## API Kimlik Bilgileri

Çiçek Sepeti Bayi Paneli'nden:

1. **Shop ID**: Mağaza ID'niz
2. **API Key**: API anahtar bilgisi

## Kurulum

1. Modülü yükle
2. **Pazaryeri → Pazaryeri Kanalları**'ndan yeni kanal oluştur
3. Kanal tipi: "Çiçek Sepeti"
4. API kimlik bilgilerini gir
5. "Bağlantıyı Test Et" butonu ile test et

## API Endpoints

### Orders
```
GET  /api/orders
GET  /api/orders/{orderId}
PUT  /api/orders/{orderId}/status
```

### Products
```
GET    /api/products
GET    /api/products/{productId}
PUT    /api/products/{productId}
```

### Stock
```
PUT    /api/products/{productId}/stock
```

### Price
```
PUT    /api/products/{productId}/price
```

## Senkronizasyon Aralıkları

- **Siparişler**: Her 15-30 dakika (hızlı tanıtım gerektiği için)
- **Stok**: Gerçek zamanlı (Odoo'da değişiklik yapıldığında)
- **Fiyat**: Saatlik

## Özel Alanlar (Çiçek Sepeti)

### Siparişlerde
- `cardNote`: Kart notu
- `deliveryTime`: Teslimat saati
- `giftWrap`: Hediye ambalajı
- `specialNote`: Özel not

## Lisans

LGPL-3
