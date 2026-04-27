{
    'name': 'Estonia Intrastat Declaration',
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'description': "Generates Intrastat XML report for declaration.",
    'depends': ['l10n_ee', 'account_intrastat'],
    'data': [
        'data/intrastat_export.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
