# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'DIN 5008 - Field Service',
    'version': '1.0',
    'category': 'Accounting/Localizations',
    'author': 'Odoo SA',
    'depends': [
        'l10n_din5008',
        'industry_fsm_report',
    ],
    'assets': {
        'web.report_assets_common': [
            'l10n_din5008_industry_fsm/static/src/**/*',
        ],
    },
    'data': [
        'report/worksheet_custom_report_templates.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
