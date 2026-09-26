{
    'name': 'Sale Extension',
    'version': '1.0',
    'depends': ['sale', 'product', 'global_utilities', 'base', 'calendar', 'mail'],
    'data': [
        'views/sale_order_form_inherit.xml',
        'views/res_partner_form_extension.xml',
        'views/res_partner_form_hide_fields.xml',
        'views/sale_order_form_file_manager.xml',
        'views/res_partner_form_inherit.xml',
        'views/res_partner_list_extension.xml',
        'views/res_partner_kanban_extension.xml',
        'views/sale_order_list_extension.xml',
        'views/sale_order_custom_templates.xml',
        # 'views/remove_email_button.xml',
        'views/mail_template_inherit.xml',
        # 'views/email_template.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'sale_extension/static/src/scss/hide_topbar.scss',
            'sale_extension/static/src/scss/hide_buttons.scss',
            'sale_extension/static/src/scss/sales_kanban_hide_fields.scss',
        ],
    },
    'installable': True,
    'application':True,
    'auto_install': False,
}