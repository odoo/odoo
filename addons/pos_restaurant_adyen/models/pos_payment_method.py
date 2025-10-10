# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    adyen_merchant_account = fields.Char(
        help="The POS merchant account code used in Adyen",
    )

    def _get_adyen_endpoints(self):
        return {
            **super()._get_adyen_endpoints(),
            "adjust": "/payments/{paymentPspReference}/amountUpdates",
            "capture": "/payments/{paymentPspReference}/captures",
        }

    @api.model
    def _load_pos_data_fields(self, config):
        params = super()._load_pos_data_fields(config)
        params += ["adyen_merchant_account"]
        return params
