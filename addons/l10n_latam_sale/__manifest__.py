# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'LATAM - Sale Report',
    'version': '1.0',
    'description': """LATAM Sale Report""",
    'category': 'Accounting/Localizations/Sale',
    'depends': [
        'l10n_latam_base',
        'sale',
    ],
    'data': [
        'report/sale_ir_actions_report_templates.xml',
    ],
    'installable': True,
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
