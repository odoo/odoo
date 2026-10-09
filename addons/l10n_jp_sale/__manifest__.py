# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Japan - Sale Document Layout',
    'countries': ['jp'],
    'category': 'Accounting/Localizations',
    'author': 'Odoo S.A.',
    'depends': [
        'l10n_jp',
        'sale',
    ],
    'data': [
        'report/ir_actions_report_templates.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
