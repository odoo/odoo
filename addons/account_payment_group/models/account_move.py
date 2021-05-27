from odoo import models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_register_payment_group(self):
        to_pay_move_lines = self.mapped('line_ids').filtered(lambda r: not r.reconciled and r.account_id.internal_type in ('payable', 'receivable'))
        if not to_pay_move_lines:
            raise UserError(_('Nothing to be paid on selected entries'))
        to_pay_partners = self.mapped('commercial_partner_id')
        if len(to_pay_partners) > 1:
            raise UserError(_('Selected recrods must be of the same partner'))

        return {
            'name': _('Register Payment'),
            'view_mode': 'form',
            'res_model': 'account.payment.group',
            'target': 'current',
            'type': 'ir.actions.act_window',
            'context': {
                'default_partner_id': to_pay_partners.id,
                'default_to_pay_move_line_ids': to_pay_move_lines.ids,
                # We set this because if became from other view and in the context has 'create=False'
                # you can't crate payment lines (for ej: subscription)
                'create': True,
                'default_company_id': self.company_id.id,
            },
        }
