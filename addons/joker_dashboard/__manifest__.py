{
    "name": "Pazaryeri & Hızlı Teslimat Dashboard",
    "version": "19.0.1.0.0",
    "category": "JOKER Platform",
    "application": True,
    "icon": "/joker_dashboard/static/description/icon.png",
    "author": "Joker Stack",
    "depends": [
        "base",
        "sale",
        "stock",
        "joker_marketplace_core",
        "joker_marketplace_trendyol",
        "joker_marketplace_hepsiburada",
        "joker_marketplace_n11",
        "joker_marketplace_cicek_sepeti",
        "joker_qcommerce_core",
        "joker_qcommerce_getir",
        "joker_qcommerce_yemeksepeti",
        "joker_qcommerce_vigo",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/dashboard_views.xml",
        "views/dashboard_menu.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
    "description": """
    Pazaryeri (Trendyol, Hepsiburada, N11, Çiçek Sepeti) ve Hızlı Teslimat (Getir, Yemeksepeti, Vigo)
    platformlarının birleştirilmiş analitik dashboard'ı.

    Özellikler:
    - Unified KPI cards (toplam sipariş, beklemede, başarı oranı)
    - Platform karşılaştırma (Pazaryeri vs Q-Commerce)
    - Senkronizasyon durumu widget'ı
    - Sipariş trend grafikleri (günlük, haftalık, aylık)
    - Kanban board (Channel, Order, Delivery status'e göre)
    - Stok devir analizi
    - Kâr marjı raporları
    - PDF export, scheduled sync
    """,
}
