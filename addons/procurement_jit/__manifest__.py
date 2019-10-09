# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Just In Time Scheduling',
    'version': '1.0',
    'category': 'Operations/Inventory',
    'description': """
This module will automatically reserve the picking from stock when a sales order is confirmed
=============================================================================================
Upon confirmation of a sales order or when quantities are added,
the picking that reserves from stock will be reserved if the
necessary quantities are available.

In the simplest configurations, this is an easy way of working:
first come, first served.  However, when not installed, you can
use manual reservation or run the schedulers where the system
will take into account the expected date and the priority.

If this automatic reservation would reserve too much, you can
still unreserve a picking.
    """,
    'depends': ['sale_stock'],
    'data': [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': True,
}
