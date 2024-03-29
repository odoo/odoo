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
        if self.product_id.cost_method == 'standard':
            # In case of standard price, the component cost is the cost of the product
            # the subcontracting service cost may not represent the real cost of the subcontracting service
            # the difference should be posted in price difference account in the end
            component_cost = currency.round(sum(m.price_unit * m.product_uom_qty for m in subcontract_production.move_raw_ids))
            subcontract_service_cost = credit_value - component_cost
        else:
            subcontract_service_cost = currency.round(subcontract_production.extra_cost * qty)
            component_cost = credit_value - subcontract_service_cost
        if not currency.is_zero(subcontract_service_cost):
            del rslt['credit_line_vals']
            service_cost_account = self.product_id.product_tmpl_id.get_product_accounts()['stock_input']
            rslt['subcontract_credit_line_vals'] = {
                'name': description,
                'product_id': self.product_id.id,
                'quantity': qty,
                'product_uom_id': self.product_id.uom_id.id,
                'ref': description,
                'partner_id': partner_id,
                'balance': -subcontract_service_cost,
                'account_id': service_cost_account.id,
            }
            rslt['component_credit_line_vals'] = {
                'name': description,
                'product_id': self.product_id.id,
                'quantity': qty,
                'product_uom_id': self.product_id.uom_id.id,
                'ref': description,
                'partner_id': partner_id,
                'balance': -component_cost,
                'account_id': credit_account_id,
            }
        # if svl passed is not linked to the move in self, the valuation is a correction and should always credit the
        # `stock_input` account as it adds directly to the value of the subcontracted product
        elif svl_id and self.stock_valuation_layer_ids.ids and svl_id not in self.stock_valuation_layer_ids.ids:
            rslt['credit_line_vals']['account_id'] = self.product_id.product_tmpl_id.get_product_accounts()['stock_input'].id
        return rslt

    def _get_dest_account(self, account_data):
        if self.raw_material_production_id.subcontractor_id:
            return account_data['production'].id
        return super()._get_dest_account(account_data)

    def _get_src_account(self, account_data):
        if self.production_id.subcontractor_id:
            return account_data['production'].id
        return super()._get_src_account(account_data)
