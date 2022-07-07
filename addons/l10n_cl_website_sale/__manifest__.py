# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Chilean eCommerce',
    'version': '0.0.1',
    'category': 'Accounting/Localizations/Website',
    'sequence': 14,
    'author': 'Blanco Martín & Asociados',
    'description': """""",
    'depends': [
        'website_sale',
        'l10n_cl',
    ],
    'data': [
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'l10n_cl_website_sale/static/src/js/fields/l10n_cl_fields.js',
        ]
    },
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
