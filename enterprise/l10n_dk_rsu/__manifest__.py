{
    'name': 'Denmark - RSU',
    'version': '1.0',
    'category': 'Accounting/Localizations/SBR',
    'summary': 'Denmark Localization - RSU',
    'description': """
RSU Denmark Localization.
============================
Submit your Tax Reports to the Danish tax authorities
    """,
    'depends': ['l10n_dk_reports'],
    'data': [
        'data/tax_report.xml',
        'wizard/tax_report_wizard.xml',
        'security/ir.model.access.csv',
        'views/template_rsu.xml',
    ],
    'installable': True,
    'license': 'OEEL-1',
}
