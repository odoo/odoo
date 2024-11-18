# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class PosOrder(models.Model):
    _inherit = "pos.order"

    def _get_partner_bank_id(self):
        bank_partner_id = super()._get_partner_bank_id()
        swiss_order = self.filtered(lambda o: o.company_id.country_code == 'CH')
        if swiss_order:
            has_pay_later = any(not pm.journal_id for pm in swiss_order.payment_ids.payment_method_id)
            bank_partner_id = bank_partner_id if has_pay_later else False
        return bank_partner_id
