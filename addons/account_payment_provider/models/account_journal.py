from odoo import api, models
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_available_payment_channels(self, payment_type):
        lines = super()._get_available_payment_channels(payment_type)

        return lines.filtered(lambda l: l.payment_provider_state != "disabled")

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_to_payment_provider(self):
        linked_providers = (
            self.env["payment.provider"]
            .sudo()
            .search([])
            .filtered(lambda p: p.journal_id.id in self.ids and p.state != "disabled")
        )
        if linked_providers:
            raise UserError(
                self.env._(
                    "You must first deactivate a payment provider before deleting its journal.\n"
                    "Linked providers: %s",
                    ", ".join(p.display_name for p in linked_providers),
                )
            )
