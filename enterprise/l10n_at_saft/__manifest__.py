# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Austrian SAF-T Export',
    'version': '1.1',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
    The Austrian Standard Audit File for Tax (SAF-T) is a standard file format for exporting various types of accounting transactional data using the XML format.
    """,
    'depends': [
        'l10n_at',
        'account_saft',
    ],
    'data': [
        'data/saft_report.xml',
        'data/l10n_at_saft.account.csv',
        'views/res_config_settings_views.xml',
        'security/ir.model.access.csv',
    ],
    'license': 'OEEL-1',
    'auto_install': ['l10n_at', 'account_saft'],
}
