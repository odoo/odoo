# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class AccountPayment(models.Model):

    _inherit = 'account.payment'

    l10n_ar_withholding_ids = fields.One2many(related='move_id.l10n_ar_withholding_ids')

    def _synchronize_to_moves(self, changed_fields):
        ''' If we change a payment with withholdings, delete all withholding lines as the synchronization mechanism is not
        implemented yet
        '''
        if not any(field_name in changed_fields for field_name in self._get_trigger_fields_to_synchronize()):
            return
        for pay in self:
            pay.move_id.line_ids.filtered(
                lambda x:
                x.account_id == pay.company_id.l10n_ar_tax_base_account_id or
                x.tax_line_id.l10n_ar_withholding_payment_type
            ).unlink()
        res = super()._synchronize_to_moves(changed_fields)
        return res
