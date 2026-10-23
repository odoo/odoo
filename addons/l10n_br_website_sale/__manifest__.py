# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Brazil - Website Sale',
    'description': 'Bridge Website Sale for Brazil',
    'category': 'Sales/Sales',
    'depends': [
        'l10n_br',
        'website_sale',
    ],
    'assets': {
        'web.assets_frontend': [
            'l10n_br_website_sale/static/src/js/**/*',
        ],
    },
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
