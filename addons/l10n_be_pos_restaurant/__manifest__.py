# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Belgian POS Restaurant Localization',
    'version': '1.0',
    'category': 'Localization/Point of Sale',
    'depends': ['pos_restaurant', 'l10n_be'],
    'auto_install': True,
    'installable': True,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
}
