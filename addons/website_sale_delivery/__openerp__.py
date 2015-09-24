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
    'depends': ['website_sale', 'delivery'],
    'data': [
        'views/delivery_carrier_templates.xml',
        'views/delivery_carrier_views.xml',
        'data/delivery_carrier_data.xml'
    ],
    'demo': [
        'data/delivery_carrier_demo.xml'
    ],
    'qweb': [],
    'installable': True,
}
