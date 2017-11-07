from openerp import models, api
from openerp.tools.translate import _
from openerp.exceptions import UserError

BKN_NO_TOUCH = _('You cannot modify anything on a %s (name: %s) that was created by point of sale operations.')


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    # Prevent modifying anything coming from the pos

    def unlink(self):
        for statement in self.filtered(lambda s: s.company_id._is_accounting_unalterable() and s.journal_id.journal_user):
            raise UserError(BKN_NO_TOUCH % (_('bank statement'), statement.name))
        return super(AccountBankStatement, self).unlink()


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    # Prevent modifying anything coming from the pos

    def unlink(self):
        for line in self.filtered(lambda s: s.company_id._is_accounting_unalterable() and s.journal_id.journal_user):
            raise UserError(BKN_NO_TOUCH % (_('bank statement line'), line.name))
        return super(AccountBankStatementLine, self).unlink()
