#!/bin/bash

# Joker modülleri yükleme scripti
set -e

MODULES=(
  "joker_queue"
  "joker_marketplace_core"
  "joker_marketplace_trendyol"
  "joker_marketplace_n11"
  "joker_marketplace_hepsiburada"
  "joker_marketplace_cicek_sepeti"
  "joker_qcommerce_core"
  "joker_qcommerce_yemeksepeti"
  "joker_qcommerce_getir"
  "joker_qcommerce_vigo"
  "joker_dashboard"
  "joker_sale_workflow"
  "custom_sync"
  "bizimhesap_connector"
)

echo "🚀 Joker modülleri yükleme başlıyor..."
echo "Database: MobilSoft"
echo ""

for module in "${MODULES[@]}"; do
  echo "📦 $module yükleniyor..."
  docker exec -T joker_odoo odoo \
    --stop-after-init \
    -i "$module" \
    -d MobilSoft \
    --log-level=warn 2>&1 | grep -E "(INFO|WARNING|ERROR|Traceback)" | tail -5 || echo "✅ $module tamam"
  sleep 3
done

echo ""
echo "✅ Tüm modüller yüklendi!"
echo ""
echo "Server adresi: http://localhost:8069"
echo "Admin kullanıcı: admin"
