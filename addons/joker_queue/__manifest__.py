# -*- coding: utf-8 -*-
{
    "name": "Joker Queue",
    "version": "19.0.1.0.0",
    "category": "JOKER Platform",
    "application": True,
    "icon": "/joker_queue/static/description/icon.png",
    "summary": "Background Job Queue - Async işlemler için kuyruk sistemi",
    "description": """
Joker Queue - Background Job Sistemi
====================================

Bu modül Odoo'ya async background job yetenekleri ekler.

Özellikler:
-----------
* Background job tanımlama ve çalıştırma
* Job kuyruğu yönetimi
* Otomatik retry mekanizması
* Job durumu takibi
* Webhook tetikleyicileri
* Cron job entegrasyonu

Kullanım:
---------
```python
# Job oluşturma
self.env['joker.queue.job'].create_job(
    name='Toplu Fatura Oluştur',
    method='_create_invoices',
    model='sale.order',
    record_ids=[1, 2, 3],
)

# Job decorator ile
@job
def heavy_task(self):
    # Uzun süren işlem
    pass
```
    """,
    "author": "JOKER Grubu",
    "website": "https://www.jokergrubu.com",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
    ],
    "data": [
        "security/joker_queue_security.xml",
        "security/ir.model.access.csv",
        "data/joker_queue_data.xml",
        "views/joker_queue_views.xml",
        "views/joker_queue_channel_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "images": ["static/description/icon.svg"],
}
