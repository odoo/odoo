{
    'name': 'Sale Extension',
    'version': '1.0',
    'depends': ['sale', 'product'],
    'data': [
        'views/sale_order_form_inherit.xml',
        'views/product_template_extension.xml',
        'views/product_template_hide_fields.xml',
        'views/sale_order_form_file_manager.xml',
        'views/res_partner_form_inherit.xml'
    ],
    'installable': True,
    'application':True,
    'auto_install': False,
}