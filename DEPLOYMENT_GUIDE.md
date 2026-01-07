# 🚀 Joker Modülleri Deployment Rehberi

## ✅ Tamamlanan Adımlar
- ✔️ Marketplace Core & Adaptörleri (Trendyol, N11, Hepsiburada, ÇiçekSepeti)
- ✔️ Q-Commerce Core & Adaptörleri (Yemeksepeti, Getir, Vigo)
- ✔️ Joker Dashboard
- ✔️ Joker Queue
- ✔️ Joker Sale Workflow
- ✔️ BizimHesap Connector
- ✔️ Custom Sync
- ✔️ .gitignore güncelleme (backup/, data/, logs/ ve payment_paytr_kt hariç tutuldu)

**Commit:** `b02c9a9e9e7f`  
**Branch:** `feature/joker-modules-setup`  
**Repository:** JokerGrubu/JokerOdoo fork'ında

---

## 🔧 Server Deployment Adımları

### 1️⃣ Repository'de Feature Branch'ı Pull Edin

```bash
# Development sunucusunda
cd /opt/joker_stack

# Feature branch'ı çekin
git fetch origin feature/joker-modules-setup
git checkout feature/joker-modules-setup

# veya doğrudan yeni bir branch oluşturup pull edin:
git pull origin feature/joker-modules-setup
```

### 2️⃣ Modülleri Kurun (Sırayla)

```bash
# Docker konteyner'da Odoo CLI kullanarak

# Temel Queue altyapısı
docker exec joker_odoo odoo -i joker_queue -d MobilSoft --stop-after-init

# Marketplace çekirdeği ve adaptörleri
docker exec joker_odoo odoo -i joker_marketplace_core,joker_marketplace_trendyol,joker_marketplace_n11,joker_marketplace_hepsiburada,joker_marketplace_cicek_sepeti -d MobilSoft --stop-after-init

# Q-Commerce çekirdeği ve adaptörleri
docker exec joker_odoo odoo -i joker_qcommerce_core,joker_qcommerce_yemeksepeti,joker_qcommerce_getir,joker_qcommerce_vigo -d MobilSoft --stop-after-init

# Dashboard ve iş akışları
docker exec joker_odoo odoo -i joker_dashboard,joker_sale_workflow -d MobilSoft --stop-after-init

# BizimHesap Connector
docker exec joker_odoo odoo -i bizimhesap_connector -d MobilSoft --stop-after-init

# Custom Sync
docker exec joker_odoo odoo -i custom_sync -d MobilSoft --stop-after-init
```

### 3️⃣ Odoo'yu Yeniden Başlatın

```bash
docker compose restart odoo
```

### 4️⃣ Modülleri Doğrulayın

Web arayüzü: `http://localhost:8069`

**Apps** → Arama yapın:
- ✅ JOKER Marketplace - Core
- ✅ JOKER Hızlı Teslimat - Core
- ✅ JOKER Dashboard
- ✅ JOKER Queue
- ✅ JOKER Satış İş Akışı
- ✅ BizimHesap B2B Connector
- ✅ Custom Sync

Hepsi "Installed" (Yüklü) durumda olmalı.

---

## 📋 Hızlı Komut Seti

```bash
#!/bin/bash
# Tüm Joker modüllerini bir seferde yükleyin:

MODULES="joker_queue,joker_marketplace_core,joker_marketplace_trendyol,joker_marketplace_n11,joker_marketplace_hepsiburada,joker_marketplace_cicek_sepeti,joker_qcommerce_core,joker_qcommerce_yemeksepeti,joker_qcommerce_getir,joker_qcommerce_vigo,joker_dashboard,joker_sale_workflow,bizimhesap_connector,custom_sync"

docker exec joker_odoo odoo -i "$MODULES" -d MobilSoft --stop-after-init
docker compose restart odoo

echo "✅ Tüm modüller yüklendi!"
```

---

## 🔄 Production Deployment Sırası

1. **Backup Al**
   ```bash
   docker exec joker_db pg_dump -U odoo MobilSoft > /backup/pre-deployment-$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Pull & Update**
   ```bash
   cd /opt/joker_stack
   git fetch origin
   git checkout feature/joker-modules-setup
   ```

3. **Modülleri Kur**
   ```bash
   # Yukarıdaki hızlı komut setini çalıştırın
   ```

4. **Test Et**
   - Marketplace modülleri: Kanal konfigürasyonu kontrol edin
   - Q-Commerce: Teslimat ayarlarını doğrulayın
   - BizimHesap: Hesap eşleştirmesini kontrol edin
   - Dashboard: Kontrol panelini açın

5. **Production'a Merge Et**
   ```bash
   git checkout 19.0
   git merge feature/joker-modules-setup
   git push origin 19.0
   ```

---

## 🐛 Sorun Giderme

### Modül Yükleme Hatası
```bash
# Session temizleyin
docker exec joker_odoo rm -rf /var/lib/odoo/sessions/*

# Odoo loglarını izleyin
docker compose logs -f odoo --tail=100
```

### Database Bağlantı Hatası
```bash
docker compose restart joker_db joker_odoo
docker exec joker_odoo odoo -i MODULE_NAME -d MobilSoft --stop-after-init
```

### Manifest Hataları
```bash
# Python syntax kontrolü
python3 -m py_compile /opt/joker_stack/addons/joker_*/\*/__manifest__.py
```

---

## 📞 Sonraki Adımlar

1. **Marketplace Konfigürasyonu**
   - Trendyol API anahtarlarını girin
   - N11, Hepsiburada hesaplarını bağlayın
   - Ürün mapping'i yapın

2. **Q-Commerce Setup**
   - Yemeksepeti, Getir, Vigo entegrasyonlarını konfigüre edin
   - Teslimat alanlarını ayarlayın
   - Webhook'ları etkinleştirin

3. **BizimHesap Senkronizasyonu**
   - Muhasebe hesaplarını eşleştirin
   - Cari kayıtlarını güncelleyin
   - Senkronizasyon planlamasını başlatın

---

**Branch:** feature/joker-modules-setup  
**Push Tarihi:** 7 Ocak 2025  
**Modül Sayısı:** 14  
**Dosya Sayısı:** 160+  
