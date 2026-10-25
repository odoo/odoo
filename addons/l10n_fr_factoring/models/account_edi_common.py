# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountEdiCommon(models.AbstractModel):
    _inherit = 'account.edi.common'

    def _edi_get_partner_bank_payee_write_vals(self, payee_values, is_factoring):
        write_vals = super()._edi_get_partner_bank_payee_write_vals(payee_values, is_factoring)
        if not is_factoring:
            return write_vals
        if payee_values.get('acc_holder_partner'):
            write_vals['acc_holder_partner_id'] = payee_values['acc_holder_partner'].id
            write_vals.setdefault('acc_holder_name', payee_values['acc_holder_partner'].name)
        write_vals['is_factoring'] = True
        return write_vals
