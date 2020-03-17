# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    def _get_replenishment_order_notification(self):
        self.ensure_one()
        production = self.env['mrp.production'].search([
            ('orderpoint_id', 'in', self.ids)
        ], order='create_date desc', limit=1)
        if production:
            action = self.env.ref('mrp.action_mrp_production_form')
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('The following replenishment order has been generated'),
                    'message': '<a href="#action=%d&id=%d&model=mrp.production" target="_blank">%s</a>' % (action.id, production.id, production.name),
                    'sticky': False,
                }
            }
        return super()._get_replenishment_order_notification()
