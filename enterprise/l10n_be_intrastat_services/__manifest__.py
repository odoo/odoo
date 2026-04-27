# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Belgian Intrastat Declaration (Services)',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Adds the support for services intrastat codes.
    """,
    'depends': ['l10n_be_intrastat', 'account_intrastat_services'],
    'data': [
        'data/account.intrastat.code.csv',
        'data/intrastat_export.xml',
        'data/intrastat_report_services_f02cms.xml',
        'data/intrastat_report_services_f01dgs.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
