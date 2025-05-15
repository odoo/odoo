{
    'name': 'Sale Extension',
    'version': '1.0',
    'depends': ['sale', 'product'],
    'data': [
        'views/sale_order_form_inherit.xml',
        'views/product_template_extension.xml',
        'views/product_template_hide_fields.xml',
        'views/res_partner_form_extension.xml',
        'views/res_partner_form_hide_fields.xml'
    ],
    'installable': True,
    'application':True,
    'auto_install': False,
}