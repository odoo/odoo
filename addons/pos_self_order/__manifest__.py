# -*- coding: utf-8 -*-
{
    'name': "pos_self_order",

    'summary': """
        Addon for the POS App that allows customers to order from their smartphone or from a kiosk""",

    'description': """
    
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    # 'depends': ['point_of_sale', 'website_sale'],
    'depends': ['point_of_sale'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/index.xml',
        'views/pay.xml',
        'views/qr_code.xml',    
        'views/custom_link_views.xml',
        'views/res_config_settings_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
    'installable': True,
    'assets': {    
        'pos_self_order.assets_self_order': [
            ('include', 'web._assets_helpers'),
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            ('include', 'web._assets_bootstrap'),
            'web/static/src/boot.js',
            'web/static/src/legacy/js/promise_extension.js',  # Legacy FIXME
            'web/static/src/env.js',
            'web/static/src/session.js',
            'web/static/src/core/utils/transitions.scss',
            'web/static/src/core/**/*',
            'web/static/src/webclient/company_service.js',
            'web/static/lib/owl/owl.js',
            'web/static/lib/owl/odoo_module.js',
            'web/static/lib/luxon/luxon.js',

            'web/static/src/views/fields/formatters.js',

            'pos_self_order/static/src/**/*',
        ],

    }

}
