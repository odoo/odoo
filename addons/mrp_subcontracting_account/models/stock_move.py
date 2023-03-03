# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _should_force_price_unit(self):
        self.ensure_one()
        return self.is_subcontract or super()._should_force_price_unit()

    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description):
        rslt = super()._generate_valuation_lines_data(partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description)

        subcontract_production = self.production_id.filtered(lambda p: p.subcontractor_id)
        if not subcontract_production:
            return rslt
        # split the credit line to two, one for component cost, one for subcontracting service cost
        currency = self.company_id.currency_id
        subcontract_service_cost = currency.round(subcontract_production.extra_cost * qty)
        if not currency.is_zero(subcontract_service_cost):
            del rslt['credit_line_vals']
            component_cost = -credit_value + subcontract_service_cost
            component_cost_account = self.product_id.product_tmpl_id.get_product_accounts()['stock_output']
            rslt['subcontract_credit_line_vals'] = {
                'name': description,
                'product_id': self.product_id.id,
                'quantity': qty,
                'product_uom_id': self.product_id.uom_id.id,
                'ref': description,
                'partner_id': partner_id,
                'balance': -subcontract_service_cost,
                'account_id': credit_account_id,
            }
            rslt['component_credit_line_vals'] = {
                'name': description,
                'product_id': self.product_id.id,
                'quantity': qty,
                'product_uom_id': self.product_id.uom_id.id,
                'ref': description,
                'partner_id': partner_id,
                'balance': component_cost,
                'account_id': component_cost_account.id,
            }
        return rslt
