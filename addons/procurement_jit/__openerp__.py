# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Just In Time Scheduling',
    'version': '1.0',
    'category': 'Base',
    'description': """
This module allows Just In Time computation of procurement orders.
==================================================================

If you install this module, you will not have to run the regular procurement
scheduler anymore (but you still need to run the minimum order point rule
scheduler, or for example let it run daily).
All procurement orders will be processed immediately, which could in some
cases entail a small performance impact.

It may also increase your stock size because products are reserved as soon
as possible and the scheduler time range is not taken into account anymore.
In that case, you can not use priorities any more on the different picking.
    """,
    'author': 'OpenERP SA',
    'website': 'https://www.odoo.com/page/manufacturing',
    'depends': ['procurement', 'stock'],
    'data': [],
    'demo': [],
    'test': ['test/procurement_jit.yml'],
    'installable': True,
    'auto_install': False,
}
