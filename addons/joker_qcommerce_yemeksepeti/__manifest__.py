{
    "name": "JOKER Yemeksepeti Entegrasyonu",
    "version": "19.0.1.0.0",
    "category": "Sales/E-Commerce",
    "author": "JOKER Dev Team",
    "depends": ["joker_qcommerce_core"],
    "data": [
        "views/menu.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
    "license": "LGPL-3",
    "summary": "Yemeksepeti (Delivery Hero) entegrasyonu",
    "description": """
    Yemeksepeti Delivery Hero API aracılığıyla restoran ve kafe teslimatı entegrasyonu.

    Özellikler:
    - Sipariş alma ve yönetimi
    - Restaurant-specific özellikleri
    - Menü kategorileri
    - Özel talimatlar
    - Webhook desteği
    - Real-time teslimat takibi

    Yemeksepeti Delivery Hero'nun global standart API'sini kullanır.
    """,
    "external_dependencies": {
        "python": ["requests", "python-dateutil"],
    },
}
