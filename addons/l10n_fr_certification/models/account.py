# -*- coding: utf-8 -*-
from hashlib import sha1

from openerp import models, api, fields
from openerp.tools.translate import _
from openerp.exceptions import UserError
from openerp.tools.misc import _consteq

ERR_MSG = _("You cannot modify a %s in order for its posted data to be updated or deleted. It is the law. Field: %s")

#forbidden fields
MOVE_FIELDS = ['date', 'journal_id', 'company_id', 'line_ids']  # remove line_ids ?
LINE_FIELDS = ['debit', 'credit', 'account_id', 'move_id']  # invoice_id, partner_id, tax_ids, tax_line_id?


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_fr_secure_sequence_number = fields.Char(readonly=True)
    l10n_fr_hash = fields.Char(readonly=True)

    def _get_new_hash(self, secure_seq_number, company_id):
        """ Returns the hash to write on journal entries when they get posted"""
        self.ensure_one()
        #find previous move
        prev_move = self.search([('state', '=', 'posted'),
            ('company_id', '=', company_id.id),
            ('l10n_fr_secure_sequence_number', '!=', False)],
            order="l10n_fr_secure_sequence_number DESC",
            limit=1)
        #build and return the hash
        return self._compute_hash(prev_move.l10n_fr_hash if prev_move else '')

    def _compute_hash(self, previous_hash):
        """ Computes the hash of the browse_record given as self, based on the hash
        of the previous record in the company's securisation sequence given as parameter"""

        def _getattrstring(obj, field_str):
            field_value = obj[field_str]
            if obj._fields[field_str].type == 'many2one':
                field_value = field_value.id
            return str(field_value)

        self.ensure_one()
        hash_string = sha1(previous_hash)
        for field in MOVE_FIELDS:
            # field delimiter to make sure the string can't be wrongly interpreted
            hash_string.update('*')
            hash_string.update(_getattrstring(self, field))

        for line in self.line_ids:
            for field in LINE_FIELDS:
                hash_string.update('*')
                hash_string.update(_getattrstring(line, field))

        return hash_string.hexdigest()

    @api.multi
    def write(self, vals):
        if self.company_id.country_id == self.env.ref('base.fr'):
            # write the hash and the secure_sequence_number when posting an account.move
            if vals.get('state') == 'posted':
                new_number = self.company_id.l10n_fr_secure_sequence_id.next_by_id()
                vals.update({'l10n_fr_secure_sequence_number': new_number,
                             'l10n_fr_hash': self._get_new_hash(new_number, self.company_id)})

            # restrict the operation in case we are trying to write a forbidden field
            if (self.state == "posted" and set(vals.keys()) & set(MOVE_FIELDS)):
                raise UserError(ERR_MSG % (self._name, ', '.join(MOVE_FIELDS)))
        return super(AccountMove, self).write(vals)

    def button_cancel(self):
        #by-pass the normal behavior/message that tells people can cancel a posted journal entry
        #if the journal allows it.
        if self.company_id.country_id == self.env.ref('base.fr'):
            raise UserError(_('You cannot modify a posted entry of a journal.'))
        super(AccountMove, self).button_cancel()

    @api.model
    def _check_hash_integrity(self, company_id):
        """Checks that all posted moves have still the same data as when they were posted

        @return: tuple with
          *  1st element being a boolean giving the result of the inalterability check
          *  2nd element being the browse record of the corrupted move in case it failed
              (None otherwise)
        """
        moves = self.search([('state', '=', 'posted'),
            ('company_id', '=', company_id.id),
            ('l10n_fr_secure_sequence_number', '!=', False)],
            order="l10n_fr_secure_sequence_number ASC")

        previous_hash = ''
        for move in moves:
            if not _consteq(move.l10n_fr_hash, move._compute_hash(previous_hash=previous_hash)):
                return False, move
            previous_hash = move.l10n_fr_hash
        return True, None

    def client_check_hash_integrity(self):
        """Makes the hash integrity check and informs the user of the result"""
        check_result, wrong_move = self._check_hash_integrity(self.env.user.company_id)
        if check_result:
            action_params = {'title': _('Success: checking the integrity of account moves'),
                             'message': _('The account moves are guaranteed to be in their original and inalterable state'),
                             'sticky': True}
        else:
            action_params = {'title': _('Failure: checking account moves inalterability failed'),
                             'message': _('Corrupted Data on move %s.') % wrong_move.id}

        return {'type': 'ir.actions.client',
                'tag': 'notify_user',
                'params': action_params}


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.multi
    def write(self, vals):
        # restrict the operation in case we are trying to write a forbidden field
        if (self.company_id.country_id.id == self.env.ref('base.fr').id and
                self.move_id.state == "posted" and set(vals.keys()) & set(LINE_FIELDS)):
            raise UserError(ERR_MSG % (self._name, ', '.join(LINE_FIELDS)))
        return super(AccountMoveLine, self).write(vals)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.multi
    def write(self, vals):
        # restrict the operation in case we are trying to write a forbidden field
        if self.company_id.country_id == self.env.ref('base.fr') and vals.get('update_posted'):
            raise UserError(ERR_MSG % (self._name, 'update_posted'))
        return super(AccountJournal, self).write(vals)

    @api.model
    def create(self, vals):
        # restrict the operation in case we are trying to set a forbidden field
        if self.company_id.country_id == self.env.ref('base.fr') and vals.get('update_posted'):
            raise UserError(ERR_MSG % (self._name, 'update_posted'))
        return super(AccountJournal, self).create(vals)
