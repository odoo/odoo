# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.tools import float_is_zero


class AccountEdiFormat(models.Model):
    _inherit = "account.edi.format"

    def _get_l10n_in_edi_line_details(self, index, line, line_tax_details):
        res = super()._get_l10n_in_edi_line_details(index, line, line_tax_details)
        sign = line.move_id.is_inbound() and -1 or 1
        quantity = line.quantity
        hsn_quantity = line.hsn_quantity
        full_discount_or_zero_quantity = line.discount == 100.00 or float_is_zero(quantity, 3)
        if full_discount_or_zero_quantity:
            unit_price_in_inr = line.currency_id._convert(
                line.price_unit,
                line.company_currency_id,
                line.company_id,
                line.date or fields.Date.context_today(self)
                )
        else:
            unit_price_in_inr = ((sign * line.balance) / (1 - (line.discount / 100))) / quantity
        if unit_price_in_inr < 0 and quantity < 0:
            # If unit price and quantity both is negative then
            # We set unit price and quantity as positive because
            # government does not accept negative in qty or unit price
            unit_price_in_inr = unit_price_in_inr * -1
            hsn_quantity = hsn_quantity * -1
        res['Qty'] = self._l10n_in_round_value(hsn_quantity or 0.0, 3)
        return res
