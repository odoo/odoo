# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
#    Odoo                                                                    #
#    Copyright (C) 2023-2024 Feddad Imad (feddad.imad@gmail.com)             #
#                                                                            #
##############################################################################


{
    'name': 'Import Order lines ( Purchase / Sale )XLS(x)',
    'version': '14.0.1.0.0',
    'author': 'feddad.imad@gmail.com',
    'website': '',
    'license': 'AGPL-3',
    'category': 'Sales,Purchase',
    'summary': "Import a purchase & a sale order from an .xls/.xlsx file",
    'depends': ['base',
                'sale',
                'purchase',
                'web'
                ],
    'data': [

        'security/ir.model.access.csv',

        'views/import_bc.xml',

        'wizard/import_purchase_order.xml',
        #'wizard/import_sale_order.xml',
    ],

    'qweb': ['static/src/xml/import_cmd.xml'],
    'images':['static/description/banner.gif'],
    'installable': True,
    'application': True,
    'demo': [],
    'test': []
}
