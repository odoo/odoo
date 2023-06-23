# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountPayment(models.Model):

    _inherit = 'account.payment'

    withholding_ids = fields.One2many(related='move_id.withholding_ids', readonly=False,)

    def _synchronize_to_moves(self, changed_fields):
        ''' If we change a payment with witholdings, delete all withholding lines as the synchronization mechanism is not
        implemented yet
        '''
        if self._context.get('skip_account_move_synchronization'):
            return

        if not any(field_name in changed_fields for field_name in self._get_trigger_fields_to_synchronize()):
            return

        for pay in self.with_context(
                skip_account_move_synchronization=True, check_move_validity=False, skip_invoice_sync=True, dynamic_unlink=True):
            pay.line_ids.filtered('tax_line_id').unlink()
            pay.line_ids.filtered('tax_ids').tax_ids = False
        res = super()._synchronize_to_moves(changed_fields)
        return res
