# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "l10n_tw_edi_ecpay",
    'countries': ['tw'],
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    "summary": """ECpay invoice module""",
    "author": "Odoo PS",
    "website": "https://www.odoo.com",
    "license": "OEEL-1",
    "depends": [
        "l10n_tw",
        "sale",
    ],
    "data": [
        "views/res_config_setting_view.xml",
        "views/sale_order_view.xml",
        "views/account_move_view.xml",
        "views/account_move_reversal_view.xml",
        "report/ecpay_invoice_report.xml",
    ],
    'assets': {
        'web.report_assets_common': [
            'l10n_tw_edi_ecpay/static/src/scss/invoice.scss',
        ],
    },
}
