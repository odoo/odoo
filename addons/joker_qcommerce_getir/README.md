# JOKER Getir Entegrasyonu

## Genel Bilgi

Getir Partner API aracılığıyla Getir Çarşı (hızlı market) ve Getir Yemek (restoran) hizmetlerinin entegrasyonu.

Getir'in özellikleri:
- **30 dakika teslimat garantisi**
- **15 dakika hazırlık süresi** (genellikle)
- **Real-time kurye tracking**
- **Webhook desteği**

## Desteklenen Hizmetler

### Getir Çarşı (GetirMarket)
- Hızlı market ve bakkaliye teslimatı
- Kategori-bazlı ürünler
- Entegre ödeme (nakit/kart)

### Getir Yemek (GetirFood)
- Restoran ve kafe teslimatı
- Özel istekler desteği
- Ürün modifikasyonları

## API Bilgileri

**Base URL:** `https://integrations.getir.com/api`

**Authentication:** Bearer Token (API Key)

**Default Ayarlar:**
- Hazırlık Süresi: 15 dakika
- Maksimum Teslimat Süresi: 30 dakika

## Kurulum

1. Modülü yükle
2. **Hızlı Teslimat → Kanallar**'dan yeni Getir kanalı oluştur
3. Kanal tipi: "getir" seçini
4. API Key'i gir
5. Merchant ID'yi gir
6. "Bağlantıyı Test Et" yapı

## API Endpoints

### Siparişler
```
GET    /merchants/{merchantId}/orders
GET    /merchants/{merchantId}/orders/{orderId}
PUT    /orders/{orderId}/status
```

### Kuryeler
```
POST   /couriers/request
GET    /couriers/{courierId}
```

### Webhooks
```
POST   /webhooks/register
POST   /webhooks/events
```

## Webhook Events

- `order.created` - Yeni sipariş oluşturuldu
- `order.status_changed` - Sipariş durumu değişti
- `courier.assigned` - Kurye atandı
- `delivery.location_updated` - Kurye konumu güncellendi
- `delivery.completed` - Teslimat tamamlandı

## Sipariş Durumları

**Getir Status:**
- PENDING - Beklemede
- ACCEPTED - Kabul edildi
- PREPARING - Hazırlanıyor
- READY - Hazır
- PICKED_UP - Kargoya çıktı
- IN_TRANSIT - Yolda
- DELIVERED - Teslim edildi
- CANCELLED - İptal edildi
- FAILED - Başarısız

**Mapping:**
```
Getir             →  QCommerce
PENDING           →  pending
ACCEPTED          →  confirmed
PREPARING         →  preparing
READY             →  ready
PICKED_UP         →  on_way
IN_TRANSIT        →  on_way
DELIVERED         →  delivered
CANCELLED         →  cancelled
```

## Ödeme Yöntemleri

```
getir              →  qcommerce
cash               →  cash
creditCard         →  card
eWallet            →  online
bankTransfer       →  online
```

## Otomatik İşlemler

### Sipariş Kabulü
`auto_accept_orders` = True ise:
- Getir'den sipariş alındığında otomatik olarak onaylanır
- Status: pending → confirmed

### Kurye Talebi
`auto_request_courier` = True ise:
- Sipariş "ready" durumuna geçtiğinde otomatik kurye talep edilir
- qcommerce.delivery kaydı oluşturulur

## Real-time Tracking

Getir webhook'u aracılığıyla:
- Kurye atandığında kurye bilgileri güncellenir
- Kurye konumu real-time güncellenir (latitude, longitude)
- Teslimat tamamlandığında otomatik güncellenir

## Senkronizasyon

**Her 15 dakikada bir** (önerilen):
- Son 24 saatin siparişleri kontrol edilir
- Yeni siparişler oluşturulur
- Durumları güncellenir

## Hata Yönetimi

Tüm API çağrıları:
- Error handling ile sarılı
- qcommerce.sync.log'a kaydedilir
- Detailed error messages

## Lisans

LGPL-3
