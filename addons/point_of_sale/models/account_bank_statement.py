# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright (C) 2004-2008 PC Solutions (<http://pcsol.be>). All Rights Reserved
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    pos_session_id = fields.Many2one('pos.session', string="Session", copy=False)
    account_id = fields.Many2one('account.account', related='journal_id.default_account_id', readonly=True)

    def button_validate_or_action(self):
        # OVERRIDE to check the consistency of the statement's state regarding the session's state.
        for statement in self:
            if statement.pos_session_id.state  in ('opened', 'closing_control') and statement.state == 'open':
                raise UserError(_("You can't validate a bank statement that is used in an opened Session of a Point of Sale."))
        return super(AccountBankStatement, self).button_validate_or_action()

    def unlink(self):
        for bs in self:
            if bs.pos_session_id:
                raise UserError(_("You cannot delete a bank statement linked to Point of Sale session."))
        return super( AccountBankStatement, self).unlink()

    @api.depends('date', 'journal_id')
    def _get_previous_statement(self):
        if 'previous_pos_session_id' not in self.env.context:
            return super(AccountBankStatement, self)._get_previous_statement()
        for st in self:
            if self.env.context['previous_pos_session_id']:
                domain = [('date', '<=', st.date), ('journal_id', '=', st.journal_id.id), ('pos_session_id', '=', self.env.context['previous_pos_session_id'])]
                previous_statement = self.search(domain, limit=1)
                st.previous_statement_id = previous_statement.id
            else:
                st.previous_statement_id = False


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    pos_statement_id = fields.Many2one('pos.order', string="POS statement", ondelete='cascade')
