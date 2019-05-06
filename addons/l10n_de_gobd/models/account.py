# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields
from odoo.tools.translate import _
from odoo.exceptions import UserError


#forbidden fields
MOVE_FIELDS = ['date', 'journal_id', 'company_id']
LINE_FIELDS = ['debit', 'credit', 'account_id', 'partner_id']


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.multi
    def write(self, vals):
        for move in self:
            if move.company_id._is_accounting_gobd_unalterable():
                # restrict the operation in case we are trying to write a forbidden field
                if (move.state == "posted" and set(vals).intersection(MOVE_FIELDS)):
                    raise UserError(_("According to the German law, you cannot modify a journal entry in order for its posted data to be updated or deleted. Unauthorized field: %s.") % ', '.join(MOVE_FIELDS))
        res = super(AccountMove, self).write(vals)
        # write the hash and the secure_sequence_number when posting an account.move
        return res

    @api.multi
    def button_cancel(self):
        #by-pass the normal behavior/message that tells people can cancel a posted journal entry
        #if the journal allows it.
        if self.company_id._is_accounting_gobd_unalterable():
            raise UserError(_('You cannot modify a posted journal entry. This ensures its inalterability.'))
        super(AccountMove, self).button_cancel()


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.multi
    def write(self, vals):
        # restrict the operation in case we are trying to write a forbidden field
        if set(vals).intersection(LINE_FIELDS):
            if any(l.company_id._is_accounting_gobd_unalterable() and l.move_id.state == 'posted' for l in self):
                raise UserError(_("According to the German law, you cannot modify a journal item in order for its posted data to be updated or deleted. Unauthorized field: %s.") % ', '.join(LINE_FIELDS))
        return super(AccountMoveLine, self).write(vals)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.onchange('update_posted')
    def _onchange_update_posted(self):
        if self.update_posted and self.company_id._is_accounting_gobd_unalterable():
            field_string = self._fields['update_posted'].get_description(self.env)['string']
            raise UserError(_("According to the German law, you cannot modify a journal in order for its posted data to be updated or deleted. Unauthorized field: %s.") % field_string)

    @api.multi
    def write(self, vals):
        # restrict the operation in case we are trying to write a forbidden field
        for journal in self:
            if journal.company_id._is_accounting_gobd_unalterable():
                if vals.get('update_posted'):
                    field_string = journal._fields['update_posted'].get_description(self.env)['string']
                    raise UserError(_("According to the German law, you cannot modify a journal in order for its posted data to be updated or deleted. Unauthorized field: %s.") % field_string)
        return super(AccountJournal, self).write(vals)

    @api.model
    def create(self, vals):
        # restrict the operation in case we are trying to set a forbidden field
        if self.company_id._is_accounting_gobd_unalterable():
            if vals.get('update_posted'):
                field_string = self._fields['update_posted'].get_description(self.env)['string']
                raise UserError(_("According to the German law, you cannot modify a journal in order for its posted data to be updated or deleted. Unauthorized field: %s.") % field_string)
        return super(AccountJournal, self).create(vals)
