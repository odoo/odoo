# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright (C) 2004-2008 PC Solutions (<http://pcsol.be>). All Rights Reserved
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    pos_session_id = fields.Many2one('pos.session', string="Session", copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        pos_session_ids = {vals['pos_session_id'] for vals in vals_list if vals.get('pos_session_id', False) is not False}
        if pos_session_ids and self.env['pos.session']._contains_unmodifiable_session(pos_session_ids):
            raise UserError(_('Cannot create an account bank statement line with an unmodifiable POS session.'))
        return super().create(vals_list)

    def write(self, vals):
        pos_essential_fields_name = {'journal_id', 'amount', 'date', 'pos_session_id', 'payment_ref', 'counterpart_account_id', 'partner_id'}
        if vals.keys() & pos_essential_fields_name:
            pos_session_id = vals.get('pos_session_id', False)
            pos_sessions = self.pos_session_id
            if pos_session_id is not False:
                pos_sessions |= self.env['pos.session'].browse(pos_session_id)
            if not pos_sessions._is_modifiable():
                raise UserError(_('Cannot (un)link/edit an account bank statement line essential data with an unmodifiable POS session.'))
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_to_pos_session(self):
        for bsl in self:
            if bsl.pos_session_id:
                raise UserError(_("You cannot delete a bank statement line linked to Point of Sale session."))
