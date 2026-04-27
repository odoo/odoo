# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Netherlands - SBR OB Nummer',
    'version': '0.3',
    'category': 'Accounting/Localizations/SBR',
    'summary': 'Fix to add the omzetbelastingnummer in Dutch Localization for SBR documents',
    'description': """
SBR Dutch Localization OB Nummer
=================================
Adds the missing field for a correct exchange through SBR
    """,
    'depends': ['l10n_nl_reports_sbr'],
    'data': [
        'views/res_company_views.xml',
    ],
    'auto_install': ['l10n_nl_reports_sbr'],
    'installable': True,
    'license': 'OEEL-1',
}
