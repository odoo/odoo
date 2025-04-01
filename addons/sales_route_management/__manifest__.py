# -*- coding: utf-8 -*-
{
    #'name': "sales_route_management",

    #'description': """
     #   Long description of module's purpose
    #""",

    #'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    #'category': 'Uncategorized',
    #'version': '0.1',

    # any module necessary for this one to work correctly
    #'depends': ['base'],

    # always loaded
    #'data': [
        # 'security/ir.model.access.csv',
     #   'views/views.xml',
      #  'views/templates.xml',
    #],
 
    
    
    'name': "Sales Route Planning",
    'summary': "Manage sales routes, visits, and inventory monitoring.",
    'author': "Mona Jamal",
    'category': "Sales",
    'version': "1.0",
    'license': 'AGPL-3',
    'depends': ['base', 'sale', 'contacts'],
    'data': [
        'views/sales_route_views.xml',
        'views/sales_visit_views.xml',
        'views/sales_dashboard.xml',
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
    ],
       # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

}
