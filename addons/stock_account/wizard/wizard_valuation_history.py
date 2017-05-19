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
        if self.compute_at_date and self.date:
            ctx = dict(
                self._context,
                history_date=self.date,
                search_default_group_by_product=True,
                search_default_group_by_location=True)

            action = self.env['ir.model.data'].xmlid_to_object('stock_account.action_stock_history')
            if not action:
                action = {
                    'view_type': 'form',
                    'view_mode': 'tree,graph,pivot',
                    'res_model': 'stock.history',
                    'type': 'ir.actions.act_window',
                }
            else:
                action = action[0].read()[0]

            action['domain'] = "[('date', '<=', '" + self.date + "')]"
            action['name'] = _('Stock Value At Date')
            action['context'] = ctx
        else:
            action = self.env.ref('stock.quantsact').read()[0]
        return action
