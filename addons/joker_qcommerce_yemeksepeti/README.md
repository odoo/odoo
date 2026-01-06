# JOKER Yemeksepeti Entegrasyonu

## Genel Bilgi

Yemeksepeti Delivery Hero API aracılığıyla restoran teslimatı entegrasyonu.

Yemeksepeti'nin özellikleri:
- **45 dakika teslimat garantisi** (İstanbul içi)
- **30 dakika hazırlık süresi** (restoran seçimine göre)
- **Restaurant-specific özellikleri**
- **Menu kategorileri**
- **Ürün modifikasyonları** (ekstra sosu, sosisi vb.)
- **Special instructions desteği**
- **Global Delivery Hero API kullanır**

## Yemeksepeti vs. Getir

| Özellik           | Getir               | Yemeksepeti           |
| ----------------- | ------------------- | --------------------- |
| Hizmet            | Market & Restaurant | **Sadece Restaurant** |
| Hazırlık Süresi   | 15 dakika           | 30 dakika             |
| Teslimat Süresi   | 30 dakika           | 45 dakika             |
| Modifikasyonlar   | X                   | ✅                     |
| Menu Kategorileri | Kısıtlı             | ✅ Tam                 |

## API Bilgileri

**Base URL:** `https://api.deliveryhero.io/api/v1`

**Authentication:** Bearer Token (API Key)

**Global Platform:** Delivery Hero (Talabat, Deliveroo, Yemeksepeti, vb.)

**Default Ayarlar:**
- Hazırlık Süresi: 30 dakika
- Maksimum Teslimat Süresi: 45 dakika

## Kurulum

1. Modülü yükle
2. **Hızlı Teslimat → Kanallar**'dan yeni Yemeksepeti kanalı oluştur
3. Kanal tipi: "yemeksepeti" seçini
4. API Key'i gir (Delivery Hero credentials)
5. Merchant ID'yi gir (Restaurant ID)
6. "Bağlantıyı Test Et" yapı

## API Endpoints

### Siparişler
```
GET    /restaurants/{restaurantId}/orders
GET    /orders/{orderId}
PUT    /orders/{orderId}/status
```

### Kuryeler
```
POST   /couriers/request
GET    /couriers/{courierId}
```

### Menu & Ürünler
```
GET    /restaurants/{restaurantId}/menu
GET    /restaurants/{restaurantId}/categories
```

### Webhooks
```
POST   /webhooks/register
POST   /webhooks/events
```

## Webhook Events

- `order.created` - Yeni sipariş oluşturuldu
- `order.status_changed` - Sipariş durumu değişti
- `order.updated` - Sipariş güncellendi
- `courier.assigned` - Kurye atandı
- `delivery.location_updated` - Kurye konumu güncellendi
- `delivery.completed` - Teslimat tamamlandı

## Sipariş Durumları

**Delivery Hero Status:**
- PENDING - Beklemede
- ACCEPTED - Kabul edildi
- PREPARING - Hazırlanıyor
- READY_FOR_PICKUP - Kargoya hazır
- PICKED_UP - Kargoya çıktı
- IN_TRANSIT - Yolda
- DELIVERED - Teslim edildi
- CANCELLED - İptal edildi
- REJECTED - Reddedildi
- FAILED - Başarısız

**Mapping:**
```
Delivery Hero      →  QCommerce
PENDING            →  pending
ACCEPTED           →  confirmed
PREPARING          →  preparing
READY_FOR_PICKUP   →  ready
PICKED_UP          →  on_way
IN_TRANSIT         →  on_way
DELIVERED          →  delivered
CANCELLED          →  cancelled
```

## Ödeme Yöntemleri

```
dh_method          →  qcommerce
cash               →  cash
creditCard         →  card
card               →  card
eWallet            →  online
online             →  online
```

## Restaurant-Specific Özellikleri

### Ürün Modifikasyonları
- Soslar ve ekstralar
- Pişiş derecesi
- Porsiyon seçenekleri

Bu veriler sipariş hatlarının `notes` alanında saklanır:
```
Döner Dürüm: Extra Sos, Acı, Büyük Porsiyon
```

### Menu Kategorileri
- Ana Yemekler
- İçecekler
- Tatlılar
- Soslar

## Otomatik İşlemler

### Sipariş Kabulü
`auto_accept_orders` = True ise:
- Yemeksepeti'den sipariş alındığında otomatik olarak onaylanır
- Status: pending → confirmed

### Kurye Talebi
`auto_request_courier` = True ise:
- Sipariş "ready" durumuna geçtiğinde otomatik kurye talep edilir
- qcommerce.delivery kaydı oluşturulur

## Real-time Tracking

Webhook aracılığıyla:
- Kurye atandığında kurye bilgileri güncellenir
- Kurye konumu real-time güncellenir (latitude, longitude)
- Teslimat tamamlandığında otomatik güncellenir

## Senkronizasyon

**Her 15-30 dakikada bir** (önerilen):
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
