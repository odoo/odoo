# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class AccountPayment(models.Model):
    _name = 'account.payment'
    _inherit = ['account.payment', 'pos.load.mixin']

    def send_refund_request(self, amount):
        self.ensure_one()
        refund_tx = self.payment_transaction_id.sudo()._refund(amount)
        if refund_tx and refund_tx.provider_id.name == 'Dummy Provider':
            refund_tx.state = 'done'
            refund_tx._post_process()
        return refund_tx and refund_tx.id

    def get_account_payment_id(self, payment_transaction_id):
        return self.search_fetch([('payment_transaction_id', '=', payment_transaction_id)], ['id'], limit=1).id

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('id', 'in', [line['online_account_payment_id'] for line in data['pos.payment']])]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id']
