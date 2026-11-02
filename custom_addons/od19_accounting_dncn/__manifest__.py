# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Thai Accounting - Debit Note / Credit Note / Remaster Invoice",
    "version": "19.0.1.0.0",
    "category": "Localization",
    "summary": "Thai DN/CN: Debit Note, Credit Note, Remaster Invoice with parent link",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": [
        "account",
        "od19_partner_thai_fields",
        "od19_accounting_features",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_move_views.xml",
        "views/dncn_reason_views.xml",
    ],
    "installable": True,
    "application": False,
    "icon": "/od19_accounting_dncn/static/description/icon.svg",
}
