# JOKER Pazaryeri - Hepsiburada Entegrasyonu

## Genel Bilgi

Hepsiburada'nın modern REST API'sini kullanarak Odoo ile entegrasyon sağlayan modüldür.

## Özellikler

### Sipariş Senkronizasyonu (İki Yönlü)
- Hepsiburada'dan siparişleri otomatik olarak çek
- Siparişleri Odoo'da satış siparişine dönüştür
- Kargo bilgisini Hepsiburada'ya gönder

### Stok Yönetimi (Bir Yönlü - Odoo → Hepsiburada)
- Odoo'daki stok değişikliklerini Hepsiburada'ya senkronize et

### Fiyat Yönetimi (Bir Yönlü - Odoo → Hepsiburada)
- Odoo'daki fiyat değişikliklerini Hepsiburada'ya senkronize et

### Webhook Desteği
- Hepsiburada webhooks'larını al ve işle

## API Kimlik Bilgileri

Hepsiburada Developer Portal'dan:

1. **Shop ID**: Mağaza ID'niz
2. **API Key**: API anahtar bilgisi

## Kurulum

1. Modülü yükle
2. **Pazaryeri → Pazaryeri Kanalları**'ndan yeni kanal oluştur
3. Kanal tipi: "Hepsiburada"
4. API kimlik bilgilerini gir
5. "Bağlantıyı Test Et" butonu ile test et

## Lisans

LGPL-3
