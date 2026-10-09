{
    'name': "Pretty Buttons",
    'version': "1.0",
    'summary': "Customizes the form status indicator buttons in Odoo",
    'license': "OPL-1",
    'currency': 'EUR',
    'price': 0.00,
    'description': """Our application allows you to change the appearance of the “Save” and “Cancel” system buttons, which will make your interface more user-friendly""",
    'category': 'Custom Development',
    'author': 'ERP-Planet',
    'website': 'https://erp-planet.com.ua',
    'depends': ['web'],
    'images': ['static/description/thumbnail.png'],

    'data': [],
    'demo': [],
    'assets': {
        'web.assets_backend': [
            'pretty_buttons/static/src/views/form/form_status_indicator/form_status_indicator.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
