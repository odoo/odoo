# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_stock_landed_costs = fields.Boolean("Landed Costs",
        help="Affect landed costs on reception operations and split them among products to update their cost price.")
    group_lot_on_invoice = fields.Boolean("Display Lots & Serial Numbers on Invoices",
                                          implied_group='stock_account.group_lot_on_invoice')
    group_stock_accounting_automatic = fields.Boolean(
        "Automatic Stock Accounting", implied_group="stock_account.group_stock_accounting_automatic")
    cost_method = fields.Selection(
        related="company_id.cost_method",
        string="Costing Method",
        required=True,
        readonly=False,
    )

    @api.onchange('cost_method')
    def onchange_cost_method(self):
        if self.cost_method == self.company_id.cost_method:
            # don't display the warning when loading the settings
            return
        return {
            'warning': {
                'title': _("Warning"),
                'message': _("You are changing your company's default costing method. Are you sure you want to make that change?"),
            }
        }

    def set_values(self):
        automatic_before = self.env.user.has_group('stock_account.group_stock_accounting_automatic')
        super().set_values()
        if automatic_before and not self.env.user.has_group('stock_account.group_stock_accounting_automatic'):
            self.env['product.category'].sudo().with_context(active_test=False).search([
                ('property_valuation', '=', 'real_time')]).property_valuation = 'manual_periodic'
