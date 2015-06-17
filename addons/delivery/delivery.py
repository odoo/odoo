# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from openerp.osv import osv
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


class delivery_carrier(osv.osv):
    _name = "delivery.carrier"

    def create_grid_lines(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        grid_line_pool = self.pool.get('delivery.grid.line')
        grid_pool = self.pool.get('delivery.grid')
        for record in self.browse(cr, uid, ids, context=context):
            # if using advanced pricing per destination: do not change
            if record.use_detailed_pricelist:
                continue

            # not using advanced pricing per destination: override grid
            grid_id = grid_pool.search(cr, uid, [('carrier_id', '=', record.id)], context=context)
            if grid_id and not (record.normal_price or record.free_if_more_than):
                grid_pool.unlink(cr, uid, grid_id, context=context)
                grid_id = None

            # Check that float, else 0.0 is False
            if not (isinstance(record.normal_price,float) or record.free_if_more_than):
                continue

            if not grid_id:
                grid_data = {
                    'name': record.name,
                    'carrier_id': record.id,
                    'sequence': 10,
                }
                grid_id = [grid_pool.create(cr, uid, grid_data, context=context)]

            lines = grid_line_pool.search(cr, uid, [('grid_id','in',grid_id)], context=context)
            if lines:
                grid_line_pool.unlink(cr, uid, lines, context=context)

            #create the grid lines
            if record.free_if_more_than:
                line_data = {
                    'grid_id': grid_id and grid_id[0],
                    'name': _('Free if more than %.2f') % record.amount,
                    'type': 'price',
                    'operator': '>=',
                    'max_value': record.amount,
                    'standard_price': 0.0,
                    'list_price': 0.0,
                }
                grid_line_pool.create(cr, uid, line_data, context=context)
            if isinstance(record.normal_price,float):
                line_data = {
                    'grid_id': grid_id and grid_id[0],
                    'name': _('Default price'),
                    'type': 'price',
                    'operator': '>=',
                    'max_value': 0.0,
                    'standard_price': record.normal_price,
                    'list_price': record.normal_price,
                }
                grid_line_pool.create(cr, uid, line_data, context=context)
        return True
