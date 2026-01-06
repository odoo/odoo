# JOKER Hızlı Teslimat - Core Framework

## Genel Bilgi

Getir, Yemeksepeti, Vigo gibi hızlı teslimat (Q-Commerce) platformlarıyla entegrasyon için core framework.

Hızlı teslimat modeli, geleneksel pazaryeri (Trendyol, Hepsiburada) modelinden çok farklıdır:

- **Geleneksel Pazaryeri**: 1-7 gün teslimat
- **Q-Commerce**: 15-60 dakika teslimat

Bu nedenle ayrı bir framework oluşturduk.

## Özellikler

### Kanal Yönetimi
- Getir, Yemeksepeti, Vigo entegrasyonu
- Platform-spesifik ayarlar
- Teslimat bölgeleri tanımı
- Otomatik sipariş kabulü

### Sipariş Yönetimi
- Sipariş alma ve takip
- Otomatik durumu güncelleme (pending → confirmed → preparing → ready → on_way → delivered)
- Satış siparişine otomatik dönüşüm
- Kargoya çıkış takibi

### Teslimat Takibi
- Kurye bilgileri (ad, telefon, araç)
- Real-time konum (latitude/longitude)
- Tahmini vs. gerçek teslimat süresi
- Gecikme uyarıları

### Webhook Desteği
- Sipariş oluşturma bildirimleri
- Sipariş durum değişiklikleri
- Teslimat güncellemeleri

### Senkronizasyon Yönetimi
- Detailed sync logs
- Hata takibi
- Performans metrikleri

## Modeller

### qcommerce.channel
Hızlı teslimat platformu kanalı

**Alanlar:**
- `name`: Kanal adı
- `platform_type`: Platform (getir, yemeksepeti, vigo)
- `active`: Aktif/Pasif
- `merchant_id`: Platform merchant ID
- `api_key`: API anahtar
- `api_secret`: API secret
- `shop_id`: Mağaza ID
- `delivery_zones`: Teslimat bölgeleri (JSON)
- `preparation_time_minutes`: Hazırlık süresi
- `max_delivery_time_minutes`: Maksimum teslimat süresi
- `auto_accept_orders`: Siparişleri otomatik kabul et
- `auto_request_courier`: Kuryeleri otomatik talep et
- `total_orders`: İstatistik - Toplam sipariş
- `total_deliveries`: İstatistik - Toplam teslimat
- `pending_orders_count`: İstatistik - Beklemede
- `success_rate`: İstatistik - Başarı oranı

**Metodlar:**
- `test_connection()`: API bağlantısını test et
- `sync_orders()`: Siparişleri senkronize et
- `action_sync_orders()`: Action - Siparişleri senkronize et

### qcommerce.order
Hızlı teslimat siparişi

**Alanlar:**
- `name`: Sipariş numarası
- `platform_order_id`: Platform sipariş ID
- `status`: Durum (pending, confirmed, preparing, ready, on_way, delivered, cancelled)
- `order_date`: Sipariş tarihi
- `confirmed_date`: Onay tarihi
- `ready_date`: Hazır tarihi
- `delivered_date`: Teslimat tarihi
- `customer_name`: Müşteri adı
- `customer_phone`: Müşteri telefonu
- `customer_email`: Müşteri e-posta
- `delivery_address`: Teslimat adresi
- `delivery_zone`: Teslimat bölgesi
- `latitude`: Enlem
- `longitude`: Boylam
- `amount_subtotal`: Ürün toplamı
- `amount_delivery`: Teslimat ücreti
- `amount_discount`: İndirim
- `amount_total`: Toplam tutar
- `payment_method`: Ödeme yöntemi
- `notes`: Notlar
- `special_requests`: Özel istekler
- `line_ids`: Sipariş hatları
- `sale_order_id`: İlişkili satış siparişi

**Metodlar:**
- `action_confirm()`: Siparişi onayla
- `action_mark_preparing()`: Hazırlanıyor olarak işaretle
- `action_mark_ready()`: Hazır olarak işaretle
- `action_mark_on_way()`: Yolda olarak işaretle
- `action_mark_delivered()`: Teslim edildi olarak işaretle
- `action_cancel()`: İptal et
- `create_sale_order()`: Satış siparişi oluştur

### qcommerce.delivery
Teslimat takibi

**Alanlar:**
- `name`: Teslimat numarası
- `platform_delivery_id`: Platform teslimat ID
- `status`: Durum (waiting, assigned, in_progress, delivered, cancelled)
- `courier_name`: Kurye adı
- `courier_phone`: Kurye telefonu
- `courier_vehicle`: Araç bilgisi
- `courier_latitude`: Kurye enlem (Real-time)
- `courier_longitude`: Kurye boylam (Real-time)
- `requested_date`: Talep tarihi
- `assigned_date`: Atanma tarihi
- `pickup_date`: Kargo alma tarihi
- `delivered_date`: Teslimat tarihi
- `estimated_delivery_minutes`: Tahmini teslimat süresi
- `actual_delivery_minutes`: Gerçek teslimat süresi

**Metodlar:**
- `action_assign_courier()`: Kurye ata
- `action_pickup()`: Kargoya çıktı olarak işaretle
- `action_delivered()`: Teslim edildi olarak işaretle
- `action_cancel()`: İptal et
- `update_courier_location()`: Kurye konumunu güncelle
- `get_delivery_time_remaining()`: Kalan teslimat süresini döndür
- `is_delayed()`: Teslimat gecikmiş mi?

### qcommerce.sync.log
Senkronizasyon logu

**Alanlar:**
- `name`: Log adı
- `operation_type`: İşlem tipi
- `status`: Durum (pending, success, error)
- `channel_id`: Kanal
- `records_processed`: İşlenen kayıt
- `records_created`: Oluşturulan kayıt
- `records_updated`: Güncellenen kayıt
- `records_failed`: Başarısız kayıt
- `duration_seconds`: Süresi
- `error_message`: Hata mesajı
- `error_details`: Hata detayları
- `start_date`: Başlama tarihi
- `end_date`: Bitiş tarihi

## Views

### Kanal Yönetimi
- **Tree View**: Tüm kanalları listele
- **Kanban View**: Kanalları platform tipine göre grupla
- **Form View**: Kanal detayları, ayarları, istatistikleri

### Sipariş Yönetimi
- **Kanban View**: Siparişleri duruma göre grupla (Board görünümü)
- **Tree View**: Tüm siparişleri listele
- **Form View**: Sipariş detayları, ürünler, teslimat, satış siparişi

### Teslimat Takibi
- **Tree View**: Teslimatları listele
- **Form View**: Teslimat detayları, kurye bilgileri, konum

### Senkronizasyon Logları
- **Tree View**: Logları listele
- **Form View**: Log detayları, hata mesajları

## Güvenlik

- **User**: Okuma, siparişleri yazma, teslimatları yazma
- **Manager**: Tüm işlemler (oku, yaz, oluştur, sil)

## İntegrasyon Akışı

```
Platform (Getir/Yemeksepeti/Vigo)
         ↓
    Webhook/API
         ↓
  qcommerce.order (oluştur)
         ↓
  auto_accept_orders = True ise → action_confirm()
         ↓
  auto_request_courier = True ise → qcommerce.delivery (oluştur)
         ↓
  Kurye atanır → action_assign_courier()
         ↓
  Kargoya çıktı → action_pickup()
         ↓
  Teslim edildi → action_delivered()
         ↓
  sale.order'ı "done" olarak işaretle
```

## Lisans

LGPL-3
