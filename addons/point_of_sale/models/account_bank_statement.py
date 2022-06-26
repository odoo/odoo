# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright (C) 2004-2008 PC Solutions (<http://pcsol.be>). All Rights Reserved
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    pos_session_id = fields.Many2one('pos.session', string="Session", copy=False)
    # TODO:PoMa check if they need to be converted
    # account_id = fields.Many2one('account.account', related='journal_id.default_account_id', readonly=True)

    # def button_validate_or_action(self):
    #     # OVERRIDE to check the consistency of the statement's state regarding the session's state.
    #     for statement in self:
    #         if statement.pos_session_id.state  in ('opened', 'closing_control') and statement.state == 'open':
    #             raise UserError(_("You can't validate a bank statement that is used in an opened Session of a Point of Sale."))
    #     return super(AccountBankStatement, self).button_validate_or_action()

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_to_pos_session(self):
        for bsl in self:
            if bsl.pos_session_id:
                raise UserError(_("You cannot delete a bank statement line linked to Point of Sale session."))
