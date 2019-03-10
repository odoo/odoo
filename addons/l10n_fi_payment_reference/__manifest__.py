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
    'name': 'Finnish Payment Reference',
    'version': '12.0.0',
    'category': 'Accounting & Finance',
    'license': 'Other proprietary',
    'description': 'Create and store structured Finnish and SEPA payment references on Invoice',
    'author': 'SprintIT, Elmeri Niemelä',
    'maintainer': 'SprintIT, Elmeri Niemelä',
    'website': 'http://www.sprintit.fi',
    'depends': [
        'account',
    ],
    'data': [
        'views/account_invoice_view.xml',
        'data/bank_reference_sequence.xml',
    ],
    'installable': True,
    'auto_install': False,
}
