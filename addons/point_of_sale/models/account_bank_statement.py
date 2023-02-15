# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright (C) 2004-2008 PC Solutions (<http://pcsol.be>). All Rights Reserved
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    pos_session_id = fields.Many2one('pos.session', string="Session", copy=False)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_to_pos_session(self):
        for bsl in self:
            if bsl.pos_session_id:
                raise UserError(_("You cannot delete a bank statement line linked to Point of Sale session."))
