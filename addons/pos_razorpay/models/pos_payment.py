from odoo import models, fields
from odoo.addons import point_of_sale


class PosPayment(point_of_sale.PosPayment):


    razorpay_reverse_ref_no = fields.Char('Razorpay Reverse Reference No.')
