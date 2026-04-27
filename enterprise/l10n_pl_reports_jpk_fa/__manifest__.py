{
    'name': 'Poland - JPK FA Reports',
    'version': '1.0',
    'description': """
        JPK FA Report for Poland

        This module provides the possibility to generate the JPK_FA in xml, for Poland.
    """,
    'category': 'Accounting/Localizations/Reporting',
    'depends': [
        'l10n_pl',
        'l10n_pl_edi',
        'account_reports',
        'base_address_extended',
    ],
    'data': [
        'data/jpk_fa_export_template.xml',
        'data/jpk_fa.xml',
        'views/jpk_fa_report_views.xml',
    ],
    'auto_install': True,
    'installable': True,
    'website': 'https://www.odoo.com/app/accounting',
    'license': 'OEEL-1',
}
