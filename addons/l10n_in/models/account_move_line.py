# -*- coding: utf-8 -*-
from odoo import api, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def _get_tax_grouping_key_from_base_line(self, business_vals, tax_vals):
        # OVERRIDE to group taxes also by product.
        res = super()._get_tax_grouping_key_from_base_line(business_vals, tax_vals)
        move = business_vals['record'].move_id
        if move.is_invoice(include_receipts=True) and move.journal_id.company_id.account_fiscal_country_id.code == 'IN':
            res['product_id'] = business_vals['record'].product_id.id
            res['product_uom_id'] = business_vals['record'].product_uom_id.id
        return res

    @api.model
    def _get_tax_grouping_key_from_tax_line(self, business_vals):
        # OVERRIDE to group taxes also by product.
        res = super()._get_tax_grouping_key_from_base_line(business_vals)
        move = business_vals['record'].move_id
        if move.is_invoice(include_receipts=True) and move.journal_id.company_id.account_fiscal_country_id.code == 'IN':
            res['product_id'] = business_vals['record'].product_id.id
            res['product_uom_id'] = business_vals['record'].product_uom_id.id
        return res
