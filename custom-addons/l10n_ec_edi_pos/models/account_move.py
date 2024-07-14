from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _l10n_ec_get_payment_data(self):
        # EXTENDS l10n_ec_edi
        # If an invoice is created from a pos order, then the payment is collected at the moment of sale.
        if self.pos_order_ids:
            payment_data = []
            for payment in self.pos_order_ids.payment_ids:
                payment_vals = {
                    'payment_code': payment.payment_method_id.l10n_ec_sri_payment_id.code,
                    'payment_name': payment.payment_method_id.l10n_ec_sri_payment_id.display_name,
                    'payment_total': abs(payment.amount),
                }
                payment_data.append(payment_vals)
            return payment_data
        return super()._l10n_ec_get_payment_data()

    def _l10n_ec_get_formas_de_pago(self):
        # EXTENDS l10n_ec_edi
        self.ensure_one()
        if self.l10n_ec_sri_payment_id.code == 'mpm' and (pos_order := self.pos_order_ids):
            return [payment.payment_method_id.l10n_ec_sri_payment_id.code for payment in pos_order.payment_ids]
        else:
            return super()._l10n_ec_get_formas_de_pago()
