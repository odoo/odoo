# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProductReplenish(models.TransientModel):
    _inherit = 'product.replenish'

    def _get_record_to_notify(self, date):
        order_line = self.env['mrp.production'].search([('write_date', '>=', date)], limit=1)
        return order_line or super()._get_record_to_notify(date)

    def _get_replenishment_order_notification_link(self, production):
        if production._name == 'mrp.production':
            action = self.env.ref('mrp.action_mrp_production_form')
            return [{
                'label': production.name,
                'url': f'#action={action.id}&id={production.id}&model=mrp.production'
            }]
        return super()._get_replenishment_order_notification_link(production)
