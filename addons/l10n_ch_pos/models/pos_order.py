from odoo import models


class PosOrder(models.Model):
    _inherit = "pos.order"

    def _get_bank_account_id(self):
        bank_partner_id = super()._get_bank_account_id()
        swiss_order = self.filtered(lambda o: o.company_id.country_code == "CH")
        if swiss_order:
            has_pay_later = any(
                not pm.journal_id
                for pm in swiss_order.payment_ids.mapped("payment_method_id")
            )
            bank_partner_id = bank_partner_id if has_pay_later else False
        return bank_partner_id
