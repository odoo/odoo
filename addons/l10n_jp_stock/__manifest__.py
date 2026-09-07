# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Japan - Total Average Cost Evaluation',
    'summary': "Evaluate the JGAAP total average cost of products over a period",
    'category': 'Accounting/Localizations',
    'depends': [
        'l10n_jp',
        'stock_account',
    ],
    'data': [
        'security/ir.access.csv',
        'wizards/total_average_cost_views.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'auto_install': True,
}
