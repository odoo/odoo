{
    'name': 'eCommerce',
    'category': 'Website',
    'summary': 'Sell Your Products Online',
    'website': 'https://www.odoo.com/page/e-commerce',
    'version': '1.0',
    'description': """
OpenERP E-Commerce
==================

        """,
    'depends': ['sale', 'website_payment', 'website_mail', 'website_portal_sale'],
    'data': [
        'data/data.xml',
        'data/web_planner_data.xml',
        'views/views.xml',
        'views/templates.xml',
        'views/payment.xml',
        'views/sale_order.xml',
        'views/snippets.xml',
        'views/report_shop_saleorder.xml',
        'res_config_view.xml',
        'security/ir.model.access.csv',
        'security/website_sale.xml',
    ],
    'demo': [
        'data/demo.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
    'application': True,
}
