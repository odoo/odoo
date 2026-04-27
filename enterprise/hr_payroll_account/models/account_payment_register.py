from odoo import models, api


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    @api.model
    def _get_line_batch_key(self, line):
        """ Used for `hr.payslip` payments generation so that each payment is assigned the correct `partner_bank_id` """
        line_batch_key = super()._get_line_batch_key(line)
        if self.env.context.get('payment_consider_partner') and not line_batch_key['partner_bank_id'] and line.partner_id:
            partner_banks = line.partner_id.commercial_partner_id.bank_ids
            if partner_banks:  # and partner_banks[0].allow_out_payment:
                line_batch_key['partner_bank_id'] = partner_banks[0].id
        return line_batch_key
