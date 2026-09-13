from odoo import fields, models


class PosPayment(models.Model):
    _inherit = "pos.payment"

    razorpay_reverse_ref_no = fields.Char(string="Razorpay Reverse Reference No.")
    razorpay_p2p_request_id = fields.Char(
        string="Razorpay p2pRequestId",
        help="Required to fetch payment status during the refund order process",
    )
