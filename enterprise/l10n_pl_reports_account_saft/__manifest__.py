{
    'name': 'Poland - SAFT Income Tax Report (JPK KR PD)',
    'version': '1.0',
    'description': """
        This module also provides the possibility to generate the JPK_KR_PD in xml, for Poland.
    """,
    'category': 'Accounting/Localizations/Reporting',
    'depends': [
        'l10n_pl_reports',
        'account_saft',
    ],
    'data': [
        'data/jpk_export_templates.xml',
    ],
    'auto_install': True,
    'installable': True,
    'website': 'https://www.odoo.com/app/accounting',
    'license': 'OEEL-1',
}
