{
    'name': 'Romanian SAF-T Export (Stocks)',
    'icon': '/account/static/description/l10n.png',
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'description': '''
This module enables generating the D.406 declaration for stocks from within Odoo.
The D.406 declaration is an XML file in the SAF-T format which Romanian companies
must submit monthly or quarterly, depending on their tax reporting period.
    ''',
    'depends': [
        'account_edi_ubl_cii',
        'l10n_ro_saft',
        'stock_account',
    ],
    'data': [
        'data/saft_report.xml',
        'views/stock_picking_type_views.xml',
    ],
    'demo': [
        'demo/stock_demo.xml',
    ],
    'license': 'OEEL-1',
    'auto_install': ['l10n_ro_saft', 'stock_account'],
}
