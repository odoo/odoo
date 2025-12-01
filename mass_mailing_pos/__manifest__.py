{
    'name': "Email Marketing and Point of Sale bridge",
    'summary': "Bridge module that unbinds a duplicate action if mass_mailing is installed",
    'author': "Odoo S.A.",
    'website': "https://www.odoo.com",
    'depends': ['mass_mailing', 'point_of_sale'],
    'auto_install': True,
    'uninstall_hook': 'uninstall_hook',
    'data': [
        'views/pos_order_view.xml',
    ],
}
