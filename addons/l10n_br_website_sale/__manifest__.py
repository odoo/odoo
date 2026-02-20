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
    'post_init_hook': '_l10n_br_website_sale_post_init_hook',
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
