# Pazaryeri & Hızlı Teslimat Dashboard

Türkiye'nin tüm pazaryeri ve hızlı teslimat platformlarının birleştirilmiş analitik dashboard'ı.

## 📊 Özellikler

### 🎯 KPI Dashboard
- **Pazaryeri Metrikler**
  - Toplam sipariş sayısı
  - Beklemede/Onaylanan/Gönderilen siparişler
  - Başarı oranı (%)
  - Toplam gelir (₺)
  - En iyi performans gösteren platform

- **Q-Commerce Metrikler**
  - Toplam sipariş sayısı
  - Beklemede/Hazırlanıyor/Yolda/Teslim Edilen siparişler
  - Başarı oranı (%)
  - Ortalama teslimat süresi (dakika)
  - Toplam gelir (₺)
  - En iyi platform

- **Genel Özet**
  - Tüm platformlardan toplam sipariş
  - Toplam gelir (₺)
  - Genel başarı oranı (%)
  - Son senkronizasyon zamanı
  - Hatalı senkronizasyon sayısı

### 📈 Channel İstatistikleri

#### Pazaryeri Channels
HTML tablosunda gösterilen:
- Kanal adı (Trendyol, Hepsiburada, N11, Çiçek Sepeti)
- Toplam sipariş
- Beklemede siparişler
- Başarılı siparişler
- Başarı yüzdesi

#### Q-Commerce Channels
HTML tablosunda gösterilen:
- Platform (Getir, Yemeksepeti, Vigo)
- Toplam sipariş
- Beklemede siparişler
- Hazırlanıyor siparişler
- Teslim edilen siparişler
- Başarı yüzdesi

### 🔄 Senkronizasyon Durumu

Dashboard.sync modeli ile:
- Her kanal için son senkronizasyon zamanı
- Sonraki planlanan senkronizasyon
- Senkronizasyon durumu (Boş, Yapıyor, Hata, Başarılı)
- Senkronize edilen kayıt sayısı
- Hata mesajları (detaylı)

**Otomatik Zamanlamalar:**
- Pazaryeri: Her 1 saat
- Q-Commerce: Her 15 dakika

**Manuel Senkronizasyon:**
Şimdi Senkronize Et butonu ile anında senkronizasyon başlatılabilir.

### 🗂️ Navigation Menu

Ana Dashboard menüsü altında:
1. 📈 **Pazaryeri Analitik** - KPI dashboard'ı
2. 🔄 **Senkronizasyon Durumu** - Sync status tracking
3. 📦 **Pazaryeri Siparişleri** - Marketplace orders
4. ⚡ **Hızlı Teslimat Siparişleri** - Q-Commerce orders
5. 🚗 **Teslimatlar** - Delivery tracking
6. 🏪 **Pazaryeri Kanalları** - Channel management
7. ⚡ **Hızlı Teslimat Kanalları** - Q-Commerce channels

## 📊 Veri Kaynakları

### Pazaryeri
- `marketplace.channel` - Trendyol, Hepsiburada, N11, Çiçek Sepeti
- `marketplace.order` - Pazaryeri siparişleri
- `marketplace.sync.log` - Pazaryeri senkronizasyon logları

### Q-Commerce (Hızlı Teslimat)
- `qcommerce.channel` - Getir, Yemeksepeti, Vigo
- `qcommerce.order` - Hızlı teslimat siparişleri
- `qcommerce.delivery` - Kurye teslimatları
- `qcommerce.sync.log` - Q-Commerce senkronizasyon logları

## 🔧 Teknik Detaylar

### Models

#### DashboardMetrics (TransientModel)
- `compute` dekoratörü ile tüm metrikler gerçek zamanlı hesaplanır
- Read-only form view (create/edit/delete yasak)
- Pazaryeri + Q-Commerce birleştirilmiş raporlama

#### DashboardSync
- Senkronizasyon durum takibi modeli
- `action_sync_now()` metodu ile manuel trigger
- Status değişimleri: idle → syncing → success/error
- next_sync otomatik hesaplanır

### Dependencies
```python
'depends': [
    'base',
    'sale',
    'stock',
    'joker_marketplace_core',
    'joker_marketplace_trendyol',
    'joker_marketplace_hepsiburada',
    'joker_marketplace_n11',
    'joker_marketplace_cicek_sepeti',
    'joker_qcommerce_core',
    'joker_qcommerce_getir',
    'joker_qcommerce_yemeksepeti',
    'joker_qcommerce_vigo',
]
```

## 📈 Kullanım Örnekleri

### KPI Dashboard Açmak
1. Dashboard menüsü → Pazaryeri Analitik
2. Tüm metrikler real-time hesaplanır
3. Platform istatistikleri HTML tablolarda gösterilir

### Senkronizasyon Durumunu İzlemek
1. Dashboard menüsü → Senkronizasyon Durumu
2. Tree view'de tüm kanallar ve durumları
3. Hatalı senkronizasyonları filtrele
4. "Şimdi Senkronize Et" butonu ile manuel başlatma

### Pazaryeri/Q-Commerce Siparişlerine Erişmek
1. Dashboard menüsü → İlgili sipariş menüsü
2. Tree/Kanban/Form view'ler available
3. Durum filtreleri ve arama mevcut

## 🎨 UI Özellikler

- **Renkli Badge'ler**: Status değişikliklerinde renk değiştirme
- **İkonlu Menüler**: Her menü öğesi semantik ikon ile
- **Responsive Tablolar**: HTML tablolar CSS bootstrap sınıfları ile
- **Inline Formlar**: Transient model bilgileri inline görüntülenir
- **Action Butonları**: Sync, refresh vb. işlemler için

## 📝 Security

Erişim kontrolü:
- `group_user` - Dashboard'u görüntüle (read-only)
- `group_sale_manager` - Senkronizasyon yönet, action'ları çalıştır

Access rules (ir.model.access.csv):
- dashboard.metrics: User(R), Manager(CRUD)
- dashboard.sync: User(R), Manager(CRUD)

## 🚀 Gelecek Geliştirmeler

- [ ] Real-time chart updates (WebSocket)
- [ ] Email notifications (error alerts)
- [ ] PDF rapor generator
- [ ] Advanced filters (date range, platform selection)
- [ ] Performance optimization (database views)
- [ ] Machine learning insights (anomaly detection)

## 📞 Support

Dashboard entegrasyonu için:
- Pazaryeri: `joker_marketplace_core` sahibi ile iletişime geçin
- Q-Commerce: `joker_qcommerce_core` sahibi ile iletişime geçin

---

**Version**: 19.0.1.0.0
**License**: LGPL-3
**Author**: Joker Stack
**Status**: Production Ready ✅
