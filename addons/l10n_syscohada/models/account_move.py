# -*- coding: utf-8 -*-
from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_fields_onchange_subtotal(self, price_subtotal=None, move_type=None, currency=None, company=None, date=None):
        self.ensure_one()
        date = self.move_id.reversed_entry_id.date if self.env.context.get('origin_date') else date
        return super()._get_fields_onchange_subtotal(
            price_subtotal=self.price_subtotal if price_subtotal is None else price_subtotal,
            move_type=self.move_id.move_type if move_type is None else move_type,
            currency=self.currency_id if currency is None else currency,
            company=self.move_id.company_id if company is None else company,
            date=self.move_id.date if date is None else date,
        )
