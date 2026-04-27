{
    'name': 'NZ - Accounting Reports',
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Accounting reports for NZ
    """,
    'website': 'https://www.odoo.com/app/accounting',
    'depends': [
        'l10n_nz', 'account_reports'
    ],
    'installable': True,
    'auto_install': ['l10n_nz', 'account_reports'],
    'license': 'OEEL-1',
}
