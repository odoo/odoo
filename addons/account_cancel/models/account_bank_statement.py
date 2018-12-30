# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, api, _
from openerp.exceptions import Warning


class BankStatement(models.Model):
    _inherit = 'account.bank.statement'

    @api.multi
    def button_draft(self):
        self.state = 'open'

    @api.multi
    def button_cancel(self):
        return super(BankStatement, self.with_context(bank_statement_cancel=True)).button_cancel()


class BankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    @api.multi
    def cancel(self):
        if not self.env.context.get('bank_statement_cancel'):
            for line in self:
                if line.statement_id.state == 'confirm':
                    raise Warning(_("Please set the bank statement to New before canceling."))
        return super(BankStatementLine, self).cancel()
