from collections import defaultdict

from odoo import api, models


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        return [('pos_order_ids', 'in', [order['id'] for order in data['pos.order']['data']])]

    @api.model
    def _load_pos_data_fields(self, config_id):
        result = super()._load_pos_data_fields(config_id)
        if self.env.company.country_id.code == 'EC':
            return ['id']
        return result

    def _l10n_ec_get_payment_data(self):
        # EXTENDS l10n_ec_edi
        # If an invoice is created from a pos order, then the payment is collected at the moment of sale.
        if self.pos_order_ids:
            payment_data = defaultdict(lambda: {'payment_total': 0})
            for payment in self.pos_order_ids.payment_ids:
                grouping_key = (payment.pos_order_id.id, payment.payment_method_id.id)
                payment_data[grouping_key].update({
                    'payment_code': payment.payment_method_id.l10n_ec_sri_payment_id.code,
                    'payment_name': payment.payment_method_id.l10n_ec_sri_payment_id.display_name,
                    'payment_total': payment_data[grouping_key]['payment_total'] + payment.amount,
                })
            return list(payment_data.values())
        return super()._l10n_ec_get_payment_data()

    def _l10n_ec_get_formas_de_pago(self):
        # EXTENDS l10n_ec_edi
        self.ensure_one()
        if self.l10n_ec_sri_payment_id.code == 'mpm' and (pos_order := self.pos_order_ids):
            return [payment.payment_method_id.l10n_ec_sri_payment_id.code for payment in pos_order.payment_ids]
        else:
            return super()._l10n_ec_get_formas_de_pago()
