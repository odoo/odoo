from odoo import models, fields

class PosPayment(models.Model):

    _inherit = "pos.payment"

    razorpay_authcode = fields.Char('Razorpay APPR Code')
    razorpay_issuer_card_no = fields.Char('Razorpay Issue Card No Last 4 digits')
    razorpay_issuer_bank = fields.Char('Razorpay Issuer Bank')
    razorpay_payment_method = fields.Char('Razorpay Payment Method')
    razorpay_reference_no = fields.Char('Razorpay Merchant Reference No.')
    razorpay_reverse_ref_no = fields.Char('Razorpay Reverse Reference No.')
    razorpay_card_scheme = fields.Char('Razorpay Card Scheme')
    razorpay_card_owner_name = fields.Char('Razorpay Card Owner Name')
