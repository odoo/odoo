{
    "name": "JOKER Getir Entegrasyonu",
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
    "summary": "Getir Çarşı ve Getir Yemek entegrasyonu",
    "description": """
    Getir Partner API aracılığıyla Getir'in hızlı teslimat hizmetlerini Odoo'ya entegre eder.

    Desteklenen Hizmetler:
    - GetirÇarşı (Market & Grocery)
    - GetirYemek (Restaurant & Catering)

    Özellikler:
    - Otomatik sipariş kabulü
    - 15 dakikalık hazırlık süresi yönetimi
    - Anında kurye talebi
    - Real-time teslimat takibi
    - Webhook desteği
    """,
    "external_dependencies": {
        "python": ["requests", "python-dateutil"],
    },
}
