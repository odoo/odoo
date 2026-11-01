# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "OD19 Accounting Payment Fee",
    "version": "19.0.1.0.0",
    "summary": "Handle payment fees (bank charges) on payments",
    "author": "OD19",
    "category": "Accounting",
    "depends": ["account"],
    "data": [
        "views/account_payment_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "icon": "/od19_accounting_payment_fee/static/description/icon.svg",
}
