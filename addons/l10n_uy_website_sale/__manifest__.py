# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Uruguay Website',
    'version': '1.0',
    'category': 'Accounting/Localizations/Website',
    'description': """ Add address Uruguay localisation fields in address page. """,
    'depends': [
        'l10n_uy',
        'website_sale',
    ],
    'data': [
        'data/ir_model_fields.xml',
        'views/website_sales_templates.xml',
    ],
    'assets': {
        'web.assets_tests': [
            'l10n_uy_website_sale/static/tests/tours/*.js',
        ],
    },
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
