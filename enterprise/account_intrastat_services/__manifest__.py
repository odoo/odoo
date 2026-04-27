# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Intrastat Reports for Services',
    'category': 'Accounting/Accounting',
    'version': '1.0',
    'description': """
Intrastat Reports for Services
==============================
    """,
    'depends': ['account_intrastat'],
    'data': [
        'data/intrastat_services_report.xml',
        'views/account_intrastat_view.xml',
        'views/product_view.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'account_intrastat_services/static/src/components/**/*',
        ],
    },
}
