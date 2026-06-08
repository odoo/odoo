# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_to_payment_provider(self):
        if self.env.context.get('force_delete'):
            return
        linked_providers = self.env['payment.provider'].sudo().search([]).filtered(
            lambda p: p.journal_id.id in self.ids
        )
        if linked_providers:
            raise UserError(_(
                "You must first uninstall a payment provider before deleting its journal.\n"
                "Linked providers: %s", ', '.join(p.display_name for p in linked_providers)
            ))
