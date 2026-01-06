# JOKER Pazaryeri Core Module

## Genel Bilgi

`joker_marketplace_core` modülü, Odoo üzerinde tüm e-ticaret pazaryeri entegrasyonları için temel framework ve base sınıfları sağlar.

## Özellikleri

### 1. **Pazaryeri Yönetimi**
- Çoklu pazaryeri entegrasyonları için merkezi yönetim
- Her pazaryeri için ayrı API kimlik bilgileri
- Otomatik senkronizasyon yönetimi (sipariş, stok, fiyat)

### 2. **Modeller**

#### marketplace.channel
Pazaryeri kanalları (N11, Trendyol, Hepsiburada vb.)

**Ana Alanlar:**
- `name`: Kanal adı
- `channel_type`: Pazaryeri türü (seçim)
- `api_key`, `api_secret`: API kimlik bilgileri
- `active`: Kanalı aktif/pasif yap
- `sync_interval`: Senkronizasyon aralığı (dakika)
- `supports_*`: Desteklenen özellikler

**İşlemler:**
- `action_sync_now()`: Hemen senkronizasyon
- `action_test_connection()`: API bağlantısını test et

#### marketplace.product
Pazaryeri ürün ilanları

**Ana Alanlar:**
- `channel_id`: Hangi pazaryeri
- `product_id`: Odoo ürünü
- `channel_product_id`: Pazaryeri tarafındaki ürün ID
- `list_price`, `sale_price`: Fiyatlandırma
- `qty_available`: Mevcut stok
- `status`: Ürün durumu

#### marketplace.order
Pazaryeri siparişleri

**Ana Alanlar:**
- `channel_order_id`: Pazaryeri sipariş ID
- `order_date`: Sipariş tarihi
- `partner_id`: Müşteri
- `amount_total`: Toplam tutar
- `status`: Sipariş durumu
- `sale_order_id`: Odoo satış siparişi
- `line_ids`: Sipariş satırları

**İşlemler:**
- `action_confirm()`: Odoo'ya aktar
- `action_mark_shipped()`: Gönderildi işaretle
- `action_mark_delivered()`: Teslim edildi işaretle

#### marketplace.sync.log
Senkronizasyon logları

**Kütüphaneler & Bağımlılıklar:**

```python
from odoo_marketplace_core.connectors import BaseMarketplaceConnector
```

### 3. **Base Connector Sınıfı**

Tüm pazaryeri connectorleri `BaseMarketplaceConnector` sınıfından türetilmelidir.

```python
class BaseMarketplaceConnector(ABC):
    """Base class for all marketplace connectors"""

    def __init__(self, channel_record):
        # Initialize with marketplace.channel record
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Test API connection"""
        pass

    @abstractmethod
    def sync_orders(self, last_sync=None) -> Dict:
        """Sync orders from marketplace"""
        pass

    @abstractmethod
    def sync_inventory(self) -> Dict:
        """Sync inventory to marketplace"""
        pass

    @abstractmethod
    def sync_prices(self) -> Dict:
        """Sync prices to marketplace"""
        pass
```

**Helper Metodlar:**
- `_create_sync_log(operation)`: Senkronizasyon logu oluştur
- `_make_api_call(method, url, **kwargs)`: API çağrısı yap
- `_process_marketplace_order(order_data)`: Siparişi işle
- `_get_or_create_product(product_data)`: Ürün oluştur
- `_update_product_inventory(product, qty)`: Stok güncelle

### 4. **API Endpoints**

#### GET /api/marketplace/channels
Tüm pazaryeri kanallarını getir

**Response:**
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "name": "Trendyol",
      "type": "trendyol",
      "active": true,
      "last_sync": "2026-01-04T10:30:00",
      "total_products": 150,
      "total_orders": 25
    }
  ]
}
```

#### POST /api/marketplace/channels/{id}/sync
Pazaryeri senkronizasyonunu başlat

#### GET /api/marketplace/orders
Pazaryeri siparişlerini listele

#### POST /api/marketplace/orders/{id}/confirm
Siparişi Odoo'ya aktar

#### GET /api/marketplace/products
Pazaryeri ürünlerini listele

#### POST /api/webhook/marketplace/{channel}
Pazaryeri webhook'ları almak için

## Kurulum

1. Modülü aktif et:
```bash
odoo -d MobilSoft -i joker_marketplace_core
```

2. **Pazaryeri → Pazaryeri Kanalları**'ndan kanal oluştur

3. API kimlik bilgilerini gir

4. **Bağlantıyı Test Et** butonuna tıkla

## Pazaryeri Connector Geliştirme

Yeni bir pazaryeri entegrasyonu geliştirmek için:

1. Modül oluştur: `joker_marketplace_{channel_name}`

2. Base connector'dan türet:

```python
from joker_marketplace_core.connectors import BaseMarketplaceConnector

class TrendyolConnector(BaseMarketplaceConnector):

    def test_connection(self) -> bool:
        # Test API connection
        response = self._make_api_call('GET', 'https://api.trendyol.com/check')
        return response.status_code == 200

    def sync_orders(self, last_sync=None):
        sync_log = self._create_sync_log('sync_orders')
        try:
            # Fetch orders from Trendyol API
            orders = self._fetch_trendyol_orders(last_sync)

            for order_data in orders:
                marketplace_order = self._process_marketplace_order(order_data)
                self._create_order_lines(marketplace_order, order_data['lines'])

            self._update_sync_log('success',
                records_processed=len(orders),
                records_created=len(orders))
        except Exception as e:
            self._log_error(str(e))

    # ... implement sync_inventory and sync_prices
```

3. Manifest dosyasına bağımlılık ekle:
```python
'depends': ['joker_marketplace_core', ...]
```

## Veritabanı İlişkileri

```
marketplace.channel
├── marketplace.product (One-to-Many)
├── marketplace.order (One-to-Many)
└── marketplace.sync.log (One-to-Many)

marketplace.order
├── marketplace.order.line (One-to-Many)
├── sale.order (Many-to-One) - Odoo satış siparişi
├── account.move (One-to-Many) - Faturalar
└── stock.picking (One-to-Many) - İrsaliyeler

marketplace.product
├── product.product (Many-to-One)
└── product.category (Many-to-Many)
```

## Senkronizasyon Akışı

1. **Pazaryeri → Odoo**
   - Pazaryeri API'sinden sipariş çek
   - marketplace.order oluştur
   - `auto_confirm_orders` True ise → sale.order oluştur
   - `auto_create_invoice` True ise → Fatura oluştur

2. **Odoo → Pazaryeri**
   - marketplace.product'ten fiyat/stok çek
   - Pazaryeri API'ye gönder
   - Senkronizasyon logu kaydet

## Loglama

```python
import logging
_logger = logging.getLogger(__name__)

_logger.info(f"[{self.channel.name}] Siparişler senkronize edildi")
_logger.error(f"Senkronizasyon hatası: {error_message}")
```

## Testler

```bash
# Tüm testleri çalıştır
python -m pytest addons/joker_marketplace_core/tests/

# Spesifik test
python -m pytest addons/joker_marketplace_core/tests/test_connector.py
```

## İletişim & Support

JOKER CEO Koordinasyon: `joker@company.com`

## Lisans

LGPL-3
