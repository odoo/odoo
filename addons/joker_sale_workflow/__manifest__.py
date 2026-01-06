# -*- coding: utf-8 -*-
{
    "name": "Joker Sale Workflow",
    "version": "19.0.1.0.0",
    "category": "JOKER Platform",
    "application": True,
    "icon": "/joker_sale_workflow/static/description/icon.png",
    "summary": "Otomatik Satış İş Akışı - Sipariş onay, fatura oluşturma",
    "description": """
Joker Sale Workflow - Otomatik Satış İş Akışı
=============================================

Bu modül satış süreçlerini otomatikleştirir.

Özellikler:
-----------
* Otomatik sipariş onaylama
* Otomatik fatura oluşturma
* Otomatik fatura onaylama
* Otomatik ödeme eşleştirme
* İş akışı kuralları tanımlama
* Koşullu otomasyon
* Webhook tetikleyicileri

İş Akışı Seçenekleri:
--------------------
* Manuel - Tüm adımlar manuel
* Yarı Otomatik - Sadece sipariş onayı otomatik
* Tam Otomatik - Tüm adımlar otomatik

Koşullar:
---------
* Müşteri bazlı (VIP müşteriler için otomatik)
* Tutar bazlı (Belirli tutar altı otomatik)
* Ürün bazlı (Belirli kategoriler için otomatik)
* Ödeme yöntemi bazlı (Kredi kartı ödemeleri için otomatik)
    """,
    "author": "JOKER Grubu",
    "website": "https://www.jokergrubu.com",
    "license": "LGPL-3",
    "depends": [
        "base",
        "sale",
        "account",
        "stock",
        "joker_queue",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/joker_sale_workflow_data.xml",
        "views/joker_sale_workflow_views.xml",
        "views/sale_order_views.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "images": ["static/description/icon.svg"],
}
