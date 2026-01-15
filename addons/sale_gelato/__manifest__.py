# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Gelato",
    'summary': "Place orders through Gelato's print-on-demand service",
    'category': 'Sales/Sales',
    'depends': ['sale', 'delivery'],
    'data': [
        'data/product_data.xml',
        'data/delivery_carrier_data.xml',  # Depends on product_data.xml
        'data/mail_template_data.xml',

        'views/delivery_carrier_views.xml',
        'views/product_document_views.xml',
        'views/product_product_views.xml',
        'views/product_template_views.xml',
        'wizards/res_config_settings_views.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
