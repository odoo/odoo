# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'E-Commerce Colombian Localization',
    'version': '1.0',
    'countries': ['co'],
    'category': 'Accounting/Localizations/Website',
    'description': """
    Colombian Localization for e-commerce.
    """,
    'depends': [
        'website_sale',
        'l10n_co_edi',
    ],
    'data': [
        'data/ir_model_fields.xml',
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'l10n_co_edi_website_sale/static/src/js/website_sale_address.js',
            'l10n_co_edi_website_sale/static/src/xml/select_menu_wrapper_template.xml',
        ],
        'web.assets_tests': [
            'l10n_co_edi_website_sale/static/tests/**/*',
        ],
    },
    'auto_install': True,
    'license': 'OEEL-1',
}
