# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'French Intrastat Declaration (Services)',
    'countries': ['fr'],
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Adds the support for services intrastat codes.
    """,
    'depends': ['l10n_fr_intrastat', 'account_intrastat_services'],
    'data': [
        'data/intrastat_export.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
