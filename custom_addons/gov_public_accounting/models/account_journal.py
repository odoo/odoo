from odoo import models
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def action_open_lock_date_wizard(self):
        self.ensure_one()
        if not self.company_id.gov_public_accounting_enabled:
            raise UserError(
                "A empresa esta em contabilidade societaria. "
                "Ative o modo GOV Public Accounting para usar bloqueio por diario."
            )
        return super().action_open_lock_date_wizard()
