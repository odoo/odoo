# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Japan - Manufacturing',
    'summary': "Value manufactured goods at their consumed components in the JGAAP total average cost",
    'category': 'Accounting/Localizations',
    'depends': [
        'l10n_jp_stock',
        'mrp_account',
    ],
    'data': [
        'wizard/total_average_cost_views.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'auto_install': True,
}
