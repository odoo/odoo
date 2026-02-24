# -*- coding: utf-8 -*-
{
    'name': 'Odoo Construction Land Acquisition',
    'version': '18.0.1.0.0',
    'author': 'Pragmatic TechSoft Pvt Ltd.',
    "website": "http://www.pragtech.co.in",
    'category': 'Land',
    'summary': 'Odoo Construction Land Acquisition odoo land acquisition land, Property Details,Land Property ,Land Proposal,Land Owners,land management, odoo land, land,construction land',
    'description': """  
Odoo Construction Land Acquisition
==================================
<keywords>
odoo construction
land acquisition
odoo land acquisition
acquisition land      
     """,
    'depends': ['sale_management', 'account', 'base', 'stock', 'sale_stock'],
    'data': [
        'security/ir.model.access.csv',
        'report/invoice_report_inheritence.xml',
        'data/product_data.xml',
        'data/ir_sequence_data.xml',
        'views/masters_view.xml',
        'views/land_acquisition_view.xml',
        'views/land_proposal_view.xml',
        'views/res_partner_view.xml',
        'views/sale_view.xml',
        'views/account_view.xml',
    ],
    'images': ['static/description/animated-construction-land-acquisation.gif'],
    'live_test_url': 'https://www.pragtech.co.in/company/proposal-form.html?id=310&name=support-construction-land-acquisition',
    'license': 'OPL-1',
    'price': 290.19,
    'currency': 'USD',
    'auto_install': False,
    'installable': True,
}
