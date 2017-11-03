from openerp import models, api, fields
from openerp.tools.translate import _
from openerp.exceptions import UserError

BKN_NO_TOUCH = _('You cannot modify anything on a %s (name: %s) that was created by point of sale operations.')


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    # Prevent modifying anything coming from the pos

    @api.multi
    def write(self, vals):
        # Even draft bank statement cannot be modified if related to the pos
        for statement in self.filtered(lambda s: s.company_id._is_accounting_unalterable() and s.journal_id.journal_user):
            if vals.keys() != ['state', 'date_done'] and not vals.keys() == ['balance_end_real']:
                raise UserError(BKN_NO_TOUCH % (_('bank statement'), statement.name))
        return super(AccountBankStatement, self).write(vals)

    def unlink(self):
        for statement in self.filtered(lambda s: s.company_id._is_accounting_unalterable() and s.journal_id.journal_user):
            raise UserError(BKN_NO_TOUCH % (_('bank statement'), statement.name))
        return super(AccountBankStatement, self).unlink()


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    # Prevent modifying anything coming from the pos

    @api.multi
    def write(self, vals):
        # Even draft bank statement line cannot be modified if related to the pos
        for line in self.filtered(lambda l: l.statement_id.company_id._is_accounting_unalterable() and l.statement_id.journal_id.journal_user):
            # Awful hack on hack see account_bank_statement.py:37
            if vals.keys() != ['state'] and not vals.keys() == ['amount'] and not vals.keys() == ['sequence']:
                raise UserError(BKN_NO_TOUCH % (_('bank statement line'), line.name))
        return super(AccountBankStatementLine, self).write(vals)

    def unlink(self):
        for line in self.filtered(lambda s: s.company_id._is_accounting_unalterable() and s.journal_id.journal_user):
            raise UserError(BKN_NO_TOUCH % (_('bank statement line'), line.name))
        return super(AccountBankStatementLine, self).unlink()
