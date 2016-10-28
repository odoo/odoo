# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _


class WizardValuationHistory(models.TransientModel):
    _name = 'wizard.valuation.history'
    _description = 'Wizard that opens the stock valuation history table'

    date = fields.Datetime('Inventory at Date', help="Choose a date to get inventory at that date. Leave empty to get current stock valuation.")

    @api.multi
    def open_table(self):
        self.ensure_one()
        if self.date:
            ctx = dict(
                self._context,
                history_date=self.date,
                search_default_group_by_product=True,
                search_default_group_by_location=True)
            return {
                'domain': "[('date', '<=', '" + self.date + "')]",
                'name': _('Stock Value At Date'),
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': 'stock.history',
                'type': 'ir.actions.act_window',
                'context': ctx,
            }
        else:
            action = self.env.ref('stock.quantsact').read()[0]
            return action
