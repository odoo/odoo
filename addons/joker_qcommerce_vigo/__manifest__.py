{
    "name": "JOKER Vigo Entegrasyonu",
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
    "summary": "Vigo hızlı teslimat entegrasyonu",
    "description": """
    Vigo API aracılığıyla aynı gün teslimat hizmeti entegrasyonu.

    Özellikler:
    - Aynı gün teslimat
    - Gerçek zamanlı sipariş takibi
    - Kurye takibi
    - Webhook desteği
    - Teslimat süresi optimizasyonu
    """,
    "external_dependencies": {
        "python": ["requests", "python-dateutil"],
    },
}
