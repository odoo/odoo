# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _load_data_params(self, config_id):
        params = super()._load_data_params(config_id)
        params['pos.payment']['fields'] + ['razorpay_authcode', 'razorpay_issuer_card_no', 'razorpay_issuer_bank',
            'razorpay_payment_method', 'razorpay_reference_no', 'razorpay_reverse_ref_no', 'razorpay_card_scheme', 'razorpay_card_owner_name']
        return params
