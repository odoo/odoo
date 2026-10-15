# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import float_compare


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _should_force_price_unit(self):
        self.ensure_one()
        return self.is_subcontract or super()._should_force_price_unit()

    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description):
        rslt = super()._generate_valuation_lines_data(partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description)

        subcontract_production = self.production_id.filtered(lambda p: p.subcontractor_id)
        rounding = self.product_id.uom_id.rounding
        if not subcontract_production or float_compare(qty, 0, precision_rounding=rounding) < 0:
            return rslt
        # split the credit line to two, one for component cost, one for subcontracting service cost
        currency = self.company_id.currency_id
        if self.product_id.cost_method == 'standard':
            # In case of standard price, the component cost is the cost of the product
            # the subcontracting service cost may not represent the real cost of the subcontracting service
            # the difference should be posted in price difference account in the end
            component_cost = abs(currency.round(sum(subcontract_production.move_raw_ids.stock_valuation_layer_ids.mapped('value'))))
            subcontract_service_cost = credit_value - component_cost
        else:
            subcontract_service_cost = currency.round(subcontract_production.extra_cost * qty)
            component_cost = credit_value - subcontract_service_cost
        if not currency.is_zero(subcontract_service_cost):
            del rslt['credit_line_vals']
            accounts = self.product_id.product_tmpl_id.get_product_accounts()
            # the components were consumed into the production location's account, or stock output by default
            component_cost_account = self.location_id.valuation_in_account_id or accounts['stock_output']
            rslt['subcontract_credit_line_vals'] = {
                'name': description,
                'product_id': self.product_id.id,
                'quantity': qty,
                'product_uom_id': self.product_id.uom_id.id,
                'ref': description,
                'partner_id': partner_id,
                'balance': -subcontract_service_cost,
                'account_id': accounts['stock_input'].id,
            }
            rslt['component_credit_line_vals'] = {
                'name': description,
                'product_id': self.product_id.id,
                'quantity': qty,
                'product_uom_id': self.product_id.uom_id.id,
                'ref': description,
                'partner_id': partner_id,
                'balance': -component_cost,
                'account_id': component_cost_account.id,
            }
        return rslt
