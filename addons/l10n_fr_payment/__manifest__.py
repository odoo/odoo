# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'France - Worldline Payment Branding',
    'countries': ['fr'],
    'summary': 'Applies CAWL/Worldline branding rules for French companies.',
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'depends': [
        'l10n_fr',
        'payment',
    ],
    'auto_install': True,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}
