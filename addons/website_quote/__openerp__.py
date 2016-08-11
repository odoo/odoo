{
    'name': 'Online Proposals',
    'category': 'Website',
    'summary': 'Sales',
    'website': 'https://www.odoo.com/page/quote-builder',
    'version': '1.0',
    'description': """
OpenERP Sale Quote Roller
=========================

        """,
    'depends': ['website', 'sale', 'mail', 'web_tip', 'payment', 'website_portal_sale', 'website_mail'],
    'data': [
        'quotation_report.xml',
        'views/website_quotation.xml',
        'views/website_quotation_backend.xml',
        'views/report_saleorder.xml',
        'views/report_quotation.xml',
        'data/website_quotation_data.xml',
        'security/ir.model.access.csv',
        'data/quotation_tip_data.xml',
    ],
    'demo': [
        'data/website_quotation_demo.xml'
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
}
