from time import time
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    end_to_end_id = fields.Char(string='End to End ID', readonly=True, compute='_compute_end_to_end_id', store=True)

    def action_draft(self):
        if any(payment.batch_payment_id and payment.payment_method_code == 'sepa_ct' and payment.batch_payment_id.payment_online_status in {'pending', 'accepted'} for payment in self):
            raise UserError(_('You cannot modify a payment that has already been sent to the bank.'))

        return super().action_draft()

    @api.depends('journal_id')
    def _compute_end_to_end_id(self):
        for payment in self:
            payment.end_to_end_id = f"{time()}{payment.journal_id.id}{payment.id}".strip()[-30:]
