# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_view_stock_valuation_layers(self):
        self.ensure_one()
        scraps = self.env['stock.scrap'].search([('picking_id', '=', self.id)])
        domain = [('id', 'in', (self.move_lines + scraps.move_id).stock_valuation_layer_ids.ids)]
        action = self.env.ref('stock_account.stock_valuation_layer_action').read()[0]
        context = literal_eval(action['context'])
        context.update(self.env.context)
        context['no_at_date'] = True
        return dict(action, domain=domain, context=context)

