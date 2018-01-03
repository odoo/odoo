# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from hashlib import sha256
from json import dumps

from odoo import models, api, fields
from odoo.tools.translate import _
from odoo.exceptions import UserError


#forbidden fields
MOVE_FIELDS = ['date', 'journal_id', 'company_id']
LINE_FIELDS = ['debit', 'credit', 'account_id', 'partner_id']


class AccountMove(models.Model):
    _inherit = "account.move"

    # TO DO in master : refactor hashing algo to go into a mixin

    l10n_fr_secure_sequence_number = fields.Integer(string="Inalteralbility No Gap Sequence #", readonly=True, copy=False)
    l10n_fr_hash = fields.Char(string="Inalterability Hash", readonly=True, copy=False)
    l10n_fr_string_to_hash = fields.Char(compute='_compute_string_to_hash', readonly=True, store=False)

    def _get_new_hash(self, secure_seq_number):
        """ Returns the hash to write on journal entries when they get posted"""
        self.ensure_one()
        #get the only one exact previous move in the securisation sequence
        prev_move = self.search([('state', '=', 'posted'),
                                 ('company_id', '=', self.company_id.id),
                                 ('l10n_fr_secure_sequence_number', '!=', 0),
                                 ('l10n_fr_secure_sequence_number', '=', int(secure_seq_number) - 1)])
        if prev_move and len(prev_move) != 1:
            raise UserError(
               _('An error occured when computing the inalterability. Impossible to get the unique previous posted journal entry.'))

        #build and return the hash
        return self._compute_hash(prev_move.l10n_fr_hash if prev_move else '')

    def _compute_hash(self, previous_hash):
        """ Computes the hash of the browse_record given as self, based on the hash
        of the previous record in the company's securisation sequence given as parameter"""
        self.ensure_one()
        hash_string = sha256(previous_hash + self.l10n_fr_string_to_hash)
        return hash_string.hexdigest()

    def _compute_string_to_hash(self):
        def _getattrstring(obj, field_str):
            field_value = obj[field_str]
            if obj._fields[field_str].type == 'many2one':
                field_value = field_value.id
            return str(field_value)

        for move in self:
            values = {}
            for field in MOVE_FIELDS:
                values[field] = _getattrstring(move, field)

            for line in move.line_ids:
                for field in LINE_FIELDS:
                    k = 'line_%d_%s' % (line.id, field)
                    values[k] = _getattrstring(line, field)
            #make the json serialization canonical
            #  (https://tools.ietf.org/html/draft-staykov-hu-json-canonical-form-00)
            move.l10n_fr_string_to_hash = dumps(values, sort_keys=True, encoding="utf-8",
                                                ensure_ascii=True, indent=None,
                                                separators=(',',':'))

    @api.multi
    def write(self, vals):
        has_been_posted = False
        for move in self:
            if move.company_id._is_accounting_unalterable():
                # write the hash and the secure_sequence_number when posting an account.move
                if vals.get('state') == 'posted':
                    has_been_posted = True

                # restrict the operation in case we are trying to write a forbidden field
                if (move.state == "posted" and set(vals).intersection(MOVE_FIELDS)):
                    raise UserError(_("According to the French law, you cannot modify a journal entry in order for its posted data to be updated or deleted. Unauthorized field: %s.") % ', '.join(MOVE_FIELDS))
                # restrict the operation in case we are trying to overwrite existing hash
                if (move.l10n_fr_hash and 'l10n_fr_hash' in vals) or (move.l10n_fr_secure_sequence_number and 'l10n_fr_secure_sequence_number' in vals):
                    raise UserError(_('You cannot overwrite the values ensuring the inalterability of the accounting.'))
        res = super(AccountMove, self).write(vals)
        # write the hash and the secure_sequence_number when posting an account.move
        if has_been_posted:
            for move in self.filtered(lambda m: m.company_id._is_accounting_unalterable() and
                                                not (m.l10n_fr_secure_sequence_number or m.l10n_fr_hash)):
                new_number = move.company_id.l10n_fr_secure_sequence_id.next_by_id()
                vals_hashing = {'l10n_fr_secure_sequence_number': new_number,
                                'l10n_fr_hash': move._get_new_hash(new_number)}
                res |= super(AccountMove, move).write(vals_hashing)
        return res

    @api.multi
    def button_cancel(self):
        #by-pass the normal behavior/message that tells people can cancel a posted journal entry
        #if the journal allows it.
        if self.company_id._is_accounting_unalterable():
            raise UserError(_('You cannot modify a posted journal entry. This ensures its inalterability.'))
        super(AccountMove, self).button_cancel()

    @api.model
    def _check_hash_integrity(self, company_id):
        """Checks that all posted moves have still the same data as when they were posted
        and raises an error with the result.
        """
        def build_move_info(move):
            entry_reference = _('(ref.: %s)')
            move_reference_string = move.ref and entry_reference % move.ref or ''
            return [move.name, move_reference_string]

        moves = self.search([('state', '=', 'posted'),
                             ('company_id', '=', company_id),
                             ('l10n_fr_secure_sequence_number', '!=', 0)],
                            order="l10n_fr_secure_sequence_number ASC")

        if not moves:
            raise UserError(_('There isn\'t any journal entry flagged for data inalterability yet for the company %s. This mechanism only runs for journal entries generated after the installation of the module France - Certification CGI 286 I-3 bis.') % self.env.user.company_id.name)
        previous_hash = ''
        start_move_info = []
        for move in moves:
            if move.l10n_fr_hash != move._compute_hash(previous_hash=previous_hash):
                raise UserError(_('Corrupted data on journal entry with id %s.') % move.id)
            if not previous_hash:
                #save the date and sequence number of the first move hashed
                start_move_info = build_move_info(move)
            previous_hash = move.l10n_fr_hash
        end_move_info = build_move_info(move)

        report_dict = {'start_move_name': start_move_info[0],
                       'start_move_ref': start_move_info[1],
                       'end_move_name': end_move_info[0],
                       'end_move_ref': end_move_info[1]}

        # Raise on success
        raise UserError(_('''Successful test !

                         The journal entries are guaranteed to be in their original and inalterable state
                         From: %(start_move_name)s %(start_move_ref)s
                         To: %(end_move_name)s %(end_move_ref)s

                         For this report to be legally meaningful, please download your certification from your customer account on Odoo.com (Only for Odoo Enterprise users).'''
                         ) % report_dict)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.multi
    def write(self, vals):
        # restrict the operation in case we are trying to write a forbidden field
        if set(vals).intersection(LINE_FIELDS):
            if any(l.company_id._is_accounting_unalterable() and l.move_id.state == 'posted' for l in self):
                raise UserError(_("According to the French law, you cannot modify a journal item in order for its posted data to be updated or deleted. Unauthorized field: %s.") % ', '.join(LINE_FIELDS))
        return super(AccountMoveLine, self).write(vals)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.onchange('update_posted')
    def _onchange_update_posted(self):
        if self.update_posted and self.company_id._is_accounting_unalterable():
            field_string = self._fields['update_posted'].get_description(self.env)['string']
            raise UserError(_("According to the French law, you cannot modify a journal in order for its posted data to be updated or deleted. Unauthorized field: %s.") % field_string)

    @api.multi
    def _is_journal_alterable(self):
        self.ensure_one()
        critical_domain = [('journal_id', '=', self.id),
                            '|', ('l10n_fr_hash', '!=', False),
                            '&', ('l10n_fr_secure_sequence_number', '!=', False),
                            ('l10n_fr_secure_sequence_number', '!=', 0)]
        if self.env['account.move'].search(critical_domain):
            raise UserError(_('It is not permitted to disable the data inalterability in this journal (%s) since journal entries have already been protected.') % (self.name, ))
        return True

    @api.multi
    def write(self, vals):
        # restrict the operation in case we are trying to write a forbidden field
        for journal in self:
            if journal.company_id._is_accounting_unalterable():
                if vals.get('update_posted'):
                    field_string = journal._fields['update_posted'].get_description(self.env)['string']
                    raise UserError(_("According to the French law, you cannot modify a journal in order for its posted data to be updated or deleted. Unauthorized field: %s.") % field_string)
        return super(AccountJournal, self).write(vals)

    @api.model
    def create(self, vals):
        # restrict the operation in case we are trying to set a forbidden field
        if self.company_id._is_accounting_unalterable():
            if vals.get('update_posted'):
                field_string = self._fields['update_posted'].get_description(self.env)['string']
                raise UserError(_("According to the French law, you cannot modify a journal in order for its posted data to be updated or deleted. Unauthorized field: %s.") % field_string)
        return super(AccountJournal, self).create(vals)
