from odoo import models, fields


class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    l10n_sg_b2g_code = fields.Char()
