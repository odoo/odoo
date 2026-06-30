from odoo import models


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def unlink(self):
        tracked_lines = self.filtered(lambda stl: stl.company_id.check_account_audit_trail)
        super(AccountBankStatementLine, tracked_lines.with_context(soft_delete=True)).unlink()
        return super(AccountBankStatementLine, self - tracked_lines).unlink()
