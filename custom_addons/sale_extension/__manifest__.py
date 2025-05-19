{
    'name': 'Sale Extension',
    'version': '1.0',
    'depends': ['sale', 'product'],
    'data': [
        'views/sale_order_form_inherit.xml',
        'views/sale_order_form_file_manager.xml',
        'views/product_template_lead_time.xml',
    ],
    'installable': True,
    'application':True,
    'auto_install': False,
}