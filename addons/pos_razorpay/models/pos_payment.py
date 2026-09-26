from odoo import api, fields, models


class PosPayment(models.Model):
    _inherit = "pos.payment"

    razorpay_reverse_ref_no = fields.Char('Razorpay Reverse Reference No.')
    razorpay_p2p_request_id = fields.Char('Razorpay p2pRequestId', help='Required to fetch payment status during the refund order process')

    @api.model
    def _get_additional_payment_fields(self):
        return super()._get_additional_payment_fields() + ['razorpay_reverse_ref_no', 'razorpay_p2p_request_id']
