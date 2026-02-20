# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Malaysia - E-invoicing (POS)",
    "countries": ["my"],
    "category": "Accounting/Localizations/EDI",
    "icon": "/account/static/description/l10n.png",
    "summary": "Consolidated E-invoicing using MyInvois",
    "description": """
    This modules allows the user to send consolidated invoices to the MyInvois system when using the POS app.
    """,
    "depends": ["l10n_my_edi", "point_of_sale"],
    "data": [
        "views/myinvois_document_pos_views.xml",
        "views/pos_order_views.xml",
        "views/product_view.xml",
        "views/res_partner_view.xml",
        "views/portal_address_templates.xml",
        "views/ticket_validation_screen.xml",
    ],
    'assets': {
        'web.assets_frontend': [
            'l10n_my_edi_pos/static/src/interactions/address.js',
        ],
    },

    'auto_install': True,
    'author': 'Odoo S.A.',
    "license": "LGPL-3",
}
