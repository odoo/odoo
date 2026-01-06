# JOKER Vigo Entegrasyonu

## Genel Bilgi

Vigo aynı gün teslimat (Same-Day Delivery) hizmeti entegrasyonu.

Vigo'nun özellikleri:
- **Aynı gün teslimat** (Same-Day Delivery)
- **60 dakika teslimat süresi** (İstanbul içi)
- **20 dakika hazırlık süresi** (optimize edilmiş)
- **Real-time kurye tracking**
- **Webhook desteği**

## Vigo vs. Getir vs. Yemeksepeti

| Özellik        | Getir               | Yemeksepeti | Vigo                  |
| -------------- | ------------------- | ----------- | --------------------- |
| Tip            | Market & Restaurant | Restaurant  | **Same-Day Delivery** |
| Hazırlık       | 15 dakika           | 30 dakika   | 20 dakika             |
| Teslimat       | 30 dakika           | 45 dakika   | **60 dakika**         |
| Kargo Ağırlığı | Hafif               | Hafif       | **Ağır**              |
| İthalatı Mal   | Kısıtlı             | Kısıtlı     | **Geniş**             |

## API Bilgileri

**Base URL:** `https://api.vigox.com/v1`

**Authentication:** Bearer Token (API Key)

**Default Ayarlar:**
- Hazırlık Süresi: 20 dakika
- Maksimum Teslimat Süresi: 60 dakika

## Kurulum

1. Modülü yükle
2. **Hızlı Teslimat → Kanallar**'dan yeni Vigo kanalı oluştur
3. Kanal tipi: "vigo" seçini
4. API Key'i gir
5. Merchant ID'yi gir
6. "Bağlantıyı Test Et" yapı

## API Endpoints

### Siparişler
```
GET    /merchants/{merchantId}/orders
GET    /orders/{orderId}
PUT    /orders/{orderId}/status
```

### Teslimatlar
```
POST   /deliveries/request
GET    /deliveries/{deliveryId}
PUT    /deliveries/{deliveryId}/status
```

### Webhooks
```
POST   /webhooks/register
POST   /webhooks/events
```

## Webhook Events

- `order.created` - Yeni sipariş oluşturuldu
- `order.status_changed` - Sipariş durumu değişti
- `delivery.assigned` - Kurye atandı
- `delivery.location_updated` - Kurye konumu güncellendi
- `delivery.completed` - Teslimat tamamlandı

## Sipariş Durumları

**Vigo Status:**
- PENDING - Beklemede
- CONFIRMED - Onaylandı
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
Vigo               →  QCommerce
PENDING            →  pending
CONFIRMED          →  confirmed
ACCEPTED           →  confirmed
PREPARING          →  preparing
READY              →  ready
PICKED_UP          →  on_way
IN_TRANSIT         →  on_way
DELIVERED          →  delivered
CANCELLED          →  cancelled
```

## Ödeme Yöntemleri

```
vigo_method        →  qcommerce
CASH               →  cash
CARD               →  card
WALLET             →  online
ONLINE             →  online
```

## Otomatik İşlemler

### Sipariş Kabulü
`auto_accept_orders` = True ise:
- Vigo'dan sipariş alındığında otomatik olarak onaylanır
- Status: pending → confirmed

### Kurye Talebi
`auto_request_courier` = True ise:
- Sipariş "ready" durumuna geçtiğinde otomatik kurye talep edilir
- qcommerce.delivery kaydı oluşturulur

## Paket Detayları

Vigo için:
- Ağırlık: 5kg (default, sipariş başına ayarlanabilir)
- Değer: Sipariş tutarı
- Özel talimatlar desteği

## Real-time Tracking

Webhook aracılığıyla:
- Kurye atandığında kurye bilgileri güncellenir
- Kurye konumu real-time güncellenir (latitude, longitude)
- Teslimat tamamlandığında otomatik güncellenir

## Senkronizasyon

**Her 30 dakikada bir** (önerilen):
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
