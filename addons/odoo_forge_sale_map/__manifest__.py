# -*- coding: utf-8 -*-
{
    'name': "Customer Sale Map",

    'summary': """
"Customer Sale Map" by OdooForge is a dynamic module designed to enhance your sales strategy with a detailed geographical visualization of your sales data. The interface offers a clear and interactive map view of your sale orders, enabling you to track customer distribution and sales performance in various regions. This tool is particularly useful for understanding market penetration and sales trends, helping you make informed decisions based on real-time sales information. With this module, you can easily locate and analyze individual sale orders, like the displayed Lumber Inc order in Stockton, providing valuable insights for business growth and customer engagement.
""",
    'description': """
"Customer Sale Map" by OdooForge is a dynamic module designed to enhance your sales strategy with a detailed geographical visualization of your sales data. The interface offers a clear and interactive map view of your sale orders, enabling you to track customer distribution and sales performance in various regions. This tool is particularly useful for understanding market penetration and sales trends, helping you make informed decisions based on real-time sales information. With this module, you can easily locate and analyze individual sale orders, like the displayed Lumber Inc order in Stockton, providing valuable insights for business growth and customer engagement.    
    """,
    'author': "Scott Weber",
    'website': "http://www.odooforge.com/customer-sale-map",
    "application":True,
    'category': 'Sales',
    'version': '16.0.1.0.0',
    'maintainer': 'Odoo Forge',
    'license': 'AGPL-3',
    'support': 'info@odooforge.com',
    'depends': ['base','sale','web'],

    'data': [
        'views/views.xml',
        'views/map_template.xml',
        'views/sale_order_form_extension.xml',
        'data/map_storage_data.xml',
        'security/ir.model.access.csv'
    ],
    'qweb': [
        'views/map_template.xml',
    ],
    'images': ['static/description/coverv16.gif'],
}
