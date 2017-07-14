# -*- coding: utf-8 -*-
from hashlib import sha256
from json import dumps

from openerp import models, api, fields
from openerp.tools.translate import _
from openerp.exceptions import UserError

ERR_MSG = _("According to the french law, you cannot modify a %s in order for its posted data to be updated or deleted. Field: %s")

#forbidden fields
MOVE_FIELDS = ['date', 'journal_id', 'company_id']
LINE_FIELDS = ['debit', 'credit', 'account_id', 'partner_id']


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_fr_secure_sequence_number = fields.Integer(readonly=True, copy=False)
    l10n_fr_hash = fields.Char(readonly=True, copy=False)
    l10n_fr_string_to_hash = fields.Char(compute='_compute_string_to_hash', readonly=True, store=False)

    def _get_new_hash(self, secure_seq_number):
        """ Returns the hash to write on journal entries when they get posted"""
        self.ensure_one()
        #get the only one exact previous move in the securisation sequence
        prev_move = self.search([('state', '=', 'posted'),
                                 ('company_id', '=', self.company_id.id),
                                 ('l10n_fr_secure_sequence_number', '=', int(secure_seq_number) - 1)])
        if prev_move and len(prev_move) != 1:
            raise UserError(
               _('Error occured when computing the hash. Impossible to get the unique previous posted move'))

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
            if move.company_id.country_id.code == 'FR':
                # write the hash and the secure_sequence_number when posting an account.move
                if vals.get('state') == 'posted':
                    has_been_posted = True

                # restrict the operation in case we are trying to write a forbidden field
                if (move.state == "posted" and set(vals).intersection(MOVE_FIELDS)):
                    raise UserError(ERR_MSG % (self._name, ', '.join(MOVE_FIELDS)))
                # restrict the operation in case we are trying to overwrite existing hash
                if (move.l10n_fr_hash and 'l10n_fr_hash' in vals) or (move.l10n_fr_secure_sequence_number and 'l10n_fr_secure_sequence_number' in vals):
                    raise UserError(_('You cannot overwrite the values ensuring the inalterability of the accounting.'))
        res = super(AccountMove, self).write(vals)
        # write the hash and the secure_sequence_number when posting an account.move
        if has_been_posted:
            for move in self.filtered(lambda m: m.company_id.country_id.code == 'FR' and
                                      not (m.l10n_fr_secure_sequence_number or m.l10n_fr_hash)):
                new_number = move.company_id.l10n_fr_secure_sequence_id.next_by_id()
                vals_hashing = {'l10n_fr_secure_sequence_number': new_number,
                                'l10n_fr_hash': move._get_new_hash(new_number)}
                res |= super(AccountMove, move).write(vals_hashing)
        return res

    def button_cancel(self):
        #by-pass the normal behavior/message that tells people can cancel a posted journal entry
        #if the journal allows it.
        if self.company_id.country_id.code == 'FR':
            raise UserError(_('You cannot modify a posted entry of a journal.'))
        super(AccountMove, self).button_cancel()

    @api.model
    def _check_hash_integrity(self, company_id):
        """Checks that all posted moves have still the same data as when they were posted
        and raises an error with the result.
        """
        moves = self.search([('state', '=', 'posted'),
                             ('company_id', '=', company_id),
                             ('l10n_fr_secure_sequence_number', '!=', 0)],
                            order="l10n_fr_secure_sequence_number ASC")

        if not moves:
            raise UserError(_('Warning: impossible to find any move with a hash.'))
        previous_hash = ''
        start_move_info = []
        for move in moves:
            if move.l10n_fr_hash != move._compute_hash(previous_hash=previous_hash):
                raise UserError(_('Corrupted Data on move %s.') % move.id)
            if not previous_hash:
                #save the date and sequence number of the first move hashed
                start_move_info = [move.date, move.l10n_fr_secure_sequence_number]
            previous_hash = move.l10n_fr_hash
        end_move_info = [move.date, move.l10n_fr_secure_sequence_number]
        raise UserError(_('''Successfully checked the integrity of account moves.

                         The account moves are guaranteed to be in their original and inalterable state
                          - since:   %s     (Sequence Number: %s)
                          - to:      %s     (Sequence Number: %s)'''
                         ) % (start_move_info[0], start_move_info[1], end_move_info[0], end_move_info[1]))


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.multi
    def write(self, vals):
        # restrict the operation in case we are trying to write a forbidden field
        if set(vals).intersection(LINE_FIELDS):
            if any(l.company_id.country_id.code == 'FR' and l.move_id.state == 'posted' for l in self):
                raise UserError(ERR_MSG % (self._name, ', '.join(LINE_FIELDS)))
        return super(AccountMoveLine, self).write(vals)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.multi
    def write(self, vals):
        # restrict the operation in case we are trying to write a forbidden field
        if self.company_id.country_id.code == 'FR' and vals.get('update_posted'):
            raise UserError(ERR_MSG % (self._name, 'update_posted'))
        return super(AccountJournal, self).write(vals)

    @api.model
    def create(self, vals):
        # restrict the operation in case we are trying to set a forbidden field
        if self.company_id.country_id.code == 'FR' and vals.get('update_posted'):
            raise UserError(ERR_MSG % (self._name, 'update_posted'))
        return super(AccountJournal, self).create(vals)
