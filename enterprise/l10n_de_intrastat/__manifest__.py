{
    'name': 'German Intrastat Declaration',
    'icon': '/account/static/description/l10n.png',
    'category': 'Accounting/Localizations/Reporting',
    'version': '1.0',
    'description': "Generates Intrastat XML report for declaration.",
    'depends': ['l10n_de', 'account_intrastat'],
    'data': [
        'data/intrastat_export.xml',
    ],
    'installable': True,
    'auto_install': ['l10n_de', 'account_intrastat'],
    'license': 'OEEL-1',
}
