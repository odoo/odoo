# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Indian - Check GST Status",
    'countries': ['in'],
    "category": "Accounting/Localizations",
    "depends": ["l10n_in_edi"],
    "data": [
        "views/account_move_views.xml",
        "views/res_partner_base_vat_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
