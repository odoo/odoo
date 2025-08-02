from odoo import fields, models


class AccountPaymentTerm(models.Model):
    _name = 'account.payment.term'
    _inherit = 'account.payment.term'

    early_pay_credit_note = fields.Boolean(string='Create Credit Note', help="Create Credit Note of early payment discount")
