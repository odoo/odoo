# -*- coding: utf-8 -*-
{
    "name": "BizimHesap Connector",
    "version": "19.0.1.0.0",
    "category": "Accounting/Integrations",
    "summary": "BizimHesap ön muhasebe ile Odoo arasında iki yönlü senkronizasyon",
    "description": """
BizimHesap Entegrasyon Modülü (MobilSoft)
========================================

Bu modül, BizimHesap ön muhasebe uygulaması ile Odoo arasında çift yönlü veri senkronizasyonu sağlar.

Neler sunar?
------------
* Cari (müşteri/tedarikçi) senkronizasyonu
* Ürün/hizmet senkronizasyonu
* Satış/alış faturaları ve ödeme/tahsilat senkronizasyonu
* Zamanlanmış otomatik senkron ile manuel tetikleme
* Tek ekrandan Hızlı Senkron paneli ve detaylı loglama

Modül Sahibi / Geliştirici: MobilSoft
Website: https://www.mobilsoft.net
    """,
    "author": "MobilSoft",
    "website": "https://www.mobilsoft.net",
    "license": "LGPL-3",
    "depends": [
        "base",
        "contacts",
        "product",
        "sale",
        "purchase",
        "account",
        "stock",
    ],
    "data": [
        # Security
        "security/bizimhesap_security.xml",
        "security/ir.model.access.csv",
        # Data
        "data/ir_sequence.xml",
        "data/ir_cron.xml",
        # Views
        "views/bizimhesap_backend_views.xml",
        "views/bizimhesap_sync_log_views.xml",
        "views/res_partner_views.xml",
        "views/product_views.xml",
        "views/account_move_views.xml",
        "views/menu_views.xml",
        # Wizards
        "wizards/sync_wizard_views.xml",
        "wizards/quick_sync_views.xml",
        "views/bizimhesap_customer_abstract_wizard_views.xml",
    ],
    "demo": [],
    "assets": {},
    "installable": True,
    "application": True,
    "auto_install": False,
    "sequence": 10,
    "images": ["static/description/icon.png"],
}
