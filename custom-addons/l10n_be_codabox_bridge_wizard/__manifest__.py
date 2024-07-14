# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'CodaBox Bridge Wizard',
    'version': '1.0',
    'author': 'Odoo',
    'website': 'https://www.odoo.com/documentation/17.0/applications/finance/fiscal_localizations/belgium.html#codabox',
    'category': 'Accounting/Localizations',
    'summary': 'For Accounting Firms',
    'description': '''This module allows Accounting Firms to connect to CodaBox
and automatically import CODA and SODA statements for their clients in Odoo.
The connection must be done by the Accounting Firm.
    ''',
    'depends': [
        'account_reports',
        'l10n_be_codabox_bridge',
    ],
    'auto_install': True,
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'wizard/connection_wizard.xml',
        'wizard/change_password_wizard.xml',
        'wizard/validation_wizard.xml',
    ],
    'license': 'OEEL-1',
}
