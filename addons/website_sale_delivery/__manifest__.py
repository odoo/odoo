{
    'name': 'eCommerce Delivery',
    'category': 'Website',
    'summary': 'Add Delivery Costs to Online Sales',
    'website': 'https://www.odoo.com/page/e-commerce',
    'version': '1.0',
    'description': """
Delivery Costs
==============
""",
    'depends': ['website_sale', 'delivery', 'website_sale_stock'],
    'data': [
        'views/website_sale_delivery_templates.xml',
        'views/website_sale_delivery_views.xml',
        'data/website_sale_delivery_data.xml'
    ],
    'demo': [
        'data/website_sale_delivery_demo.xml'
    ],
    'qweb': [],
    'installable': True,
}
