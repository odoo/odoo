{
    'name': 'Sale Extension',
    'version': '1.0',
    'depends': ['sale', 'product'],
    'data': [
        'views/sale_order_form_inherit.xml',
        'views/product_template_lead_time.xml',
        'views/product_template_form_inherit.xml',
    ],
    'installable': True,
    'application':True,
    'auto_install': False,
}