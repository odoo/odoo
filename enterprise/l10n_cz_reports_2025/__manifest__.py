{
    'name': 'Czech Republic - Accounting Reports 2025',
    'icon': '/account/static/description/l10n.png',
    'version': '1.0',
    'description': """
This module adds the following reports for the Czech Republic:
==============================================================
1. VAT Control Statement (creation and XML export). For more information, see https://adisspr.mfcr.cz/dpr/adis/idpr_pub/epo2_info/popis_struktury_detail.faces?zkratka=DPHKH1

2. Souhrnné hlášení VIES Report (creation and XML export). For more information, see https://adisspr.mfcr.cz/dpr/adis/idpr_pub/epo2_info/popis_struktury_detail.faces?zkratka=DPHSHV

3. Tax report (XML export). For more information, see https://adisspr.mfcr.cz/dpr/adis/idpr_pub/epo2_info/popis_struktury_detail.faces?zkratka=DPHDP3
    """,
    'category': 'Accounting/Localizations/Reporting',
    'depends': ['l10n_cz_reports'],
    'data': [
        'data/common_report_export.xml',
        'data/control_statement_report_export.xml',
        'data/control_statement_report.xml',
        'data/l10n_cz.tax_office.csv',
        'data/tax_report_export.xml',
        'data/vies_summary_report_export.xml',
        'data/vies_summary_report.xml',
        'views/account_move_views.xml',
        'views/account_tax_views.xml',
        'views/product_template_views.xml',
        'views/res_company_view.xml',
        'views/tax_office_view.xml',
        'security/ir.model.access.csv',
    ],
    'post_init_hook': '_l10n_cz_reports_2025_post_init',
    'auto_install': True,
    'installable': True,
    'license': 'OEEL-1',
}
