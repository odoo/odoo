# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2011 CCI Connect asbl (http://www.cciconnect.be) All Rights Reserved.
#                       Philmer <philmer@cciconnect.be>

{
    'name': 'Accounting Sequence',
    'version': '1.0',
    'category': 'Hidden',
    'description': "Change the way `sequence.mixin` works to reduce concurrency errors",
    'depends': ['account'],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
