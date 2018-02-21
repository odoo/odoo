# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _


class WizardValuationHistory(models.TransientModel):
    _name = 'wizard.valuation.history'
    _description = 'Wizard that opens the stock valuation history table'

    choose_date = fields.Boolean('Inventory at Date')
    date = fields.Datetime('Date', default=fields.Datetime.now, required=True)

    @api.multi
    def open_table(self):
        self.ensure_one()
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
        return action
