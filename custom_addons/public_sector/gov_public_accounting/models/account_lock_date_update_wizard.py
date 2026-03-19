from odoo import models
from odoo.exceptions import UserError


class AccountLockDateUpdateWizard(models.TransientModel):
    _inherit = "account.lock.date.update.wizard"

    def _ensure_public_accounting_enabled(self):
        for wizard in self:
            if not wizard.company_id.gov_public_accounting_enabled:
                raise UserError(
                    "A empresa selecionada esta em contabilidade societaria. "
                    "Ative GOV Public Accounting para alterar lock date publico."
                )

    def action_apply(self):
        self._ensure_public_accounting_enabled()
        return super().action_apply()

    def action_apply_and_lock_journals(self):
        self._ensure_public_accounting_enabled()
        return super().action_apply_and_lock_journals()
