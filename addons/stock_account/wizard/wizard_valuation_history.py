# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _


class WizardValuationHistory(models.TransientModel):
    _name = 'wizard.valuation.history'
    _description = 'Wizard that opens the stock valuation history table'

    compute_at_date = fields.Selection([
        (0, 'Current Inventory'),
        (1, 'At a Specific Date')
        ], string="Compute", help="Choose to analyze the current inventory or from a specific date in the past.")
    date = fields.Datetime('Inventory at Date', help="Choose a date to get the inventory at that date", default=fields.Datetime.now())

    @api.multi
    def open_table(self):
        self.ensure_one()

        # Call `_fifo_vacuum` on concerned moves
        fifo_valued_products = self.env['product.product']
        fifo_valued_products |= self.env['product.template'].search([('property_cost_method', '=', 'fifo')]).mapped('product_variant_ids')
        fifo_valued_categories = self.env['product.category'].search([('property_cost_method', '=', 'fifo')])
        fifo_valued_products |= self.env['product.product'].search([('categ_id', 'child_of', fifo_valued_categories.ids)])
        moves_to_vacuum = self.env['stock.move']
        Move = self.env['stock.move']
        for product in fifo_valued_products:
            moves_to_vacuum |= Move.search([('product_id', '=', product.id), ('remaining_qty', '<', 0)] + Move._get_all_base_domain())
        moves_to_vacuum._fifo_vacuum()

        if self.compute_at_date and self.date:
            action = self.env['ir.model.data'].xmlid_to_object('stock_account.stock_move_valuation_action')
            if not action:
                action = {
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'stock.move',
                    'type': 'ir.actions.act_window',
                }
            else:
                action = action[0].read()[0]

            action['domain'] = "[('date', '<=', '" + self.date + "')]"
            action['name'] = _('Stock Value At Date')
        else:
            action = self.env.ref('stock_account.product_valuation_action').read()[0]
        return action
