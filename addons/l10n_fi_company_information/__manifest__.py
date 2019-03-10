# -*- coding: utf-8 -*-
##############################################################################
#
#    ODOO Open Source Management Solution
#
#    ODOO Addon module by Sprintit Ltd
#    Copyright (C) 2018 Sprintit Ltd (<http://sprintit.fi>).
#
##############################################################################

{
    'name': 'Finnish Company Information',
    'version': '12.0.0',
    'category': 'General',
    'license': 'LGPL-3',
    'description': 'Company information additional fields, standard for Finnish companies',
    'author': 'SprintIT, Roy Nurmi',
    'maintainer': 'SprintIT, Roy Nurmi',
    'website': 'http://www.sprintit.fi',
    'depends': [
      'base',
      'account',
    ],
    'data': [
      'view/res_partner_view.xml',
    ],
    'demo': [
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
 }
