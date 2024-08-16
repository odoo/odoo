from odoo import models, fields

class PosPayment(models.Model):

    _inherit = "pos.payment"

    razorpay_reverse_ref_no = fields.Char('Razorpay Reverse Reference No.')
