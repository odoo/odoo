# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_date, groupby


class ResCompany(models.Model):
    _inherit = "res.company"

    def _check_hash_integrity(self):
        """Checks that all posted moves have still the same data as when they were posted
        and raises an error with the result.
        """
        if self.account_fiscal_country_id.code != 'PT':
            return super()._check_hash_integrity()

        if not self.env.user.has_group('account.group_account_user'):
            raise UserError(_('Please contact your accountant to print the Hash integrity result.'))

        def build_move_info(move):
            return(move.name, move.inalterable_hash, fields.Date.to_string(move.date))

        journals = self.env['account.journal'].search([('company_id', '=', self.id)])
        results = []

        self.env['account.move'].l10n_pt_compute_missing_hashes(self.env.company.id)

        for journal in journals:
            if not journal.restrict_mode_hash_table:
                results.append({
                    'name': f"{journal.name} [{journal.code}]",
                    'status': 'not_checked',
                    'msg': _('This journal is not in strict mode.'),
                })
                continue

            # We need the `sudo()` to ensure that all the moves are searched, no matter the user's access rights.
            # This is required in order to generate consistent hashes.
            # It is not an issue, since the data is only used to compute a hash and not to return the actual values.
            all_moves = self.env['account.move'].sudo().search([
                ('journal_id', '=', journal.id),
                ('inalterable_hash', '!=', False),
            ])
            if not all_moves:
                results.append({
                    'name': f"{journal.name} [{journal.code}]",
                    'status': 'no_data',
                    'msg': _('There is no journal entry flagged for data inalterability yet.'),
                })
                continue

            grouped = groupby(all_moves, key=lambda m: m.sequence_prefix)

            hash_corrupted = False
            for prefix, moves in grouped:
                moves = sorted(moves, key=lambda m: m.sequence_number)
                previous_hash = ''
                from odoo.models import Model
                for move in moves:
                    if not move._l10n_pt_verify_integrity(previous_hash):
                        results.append({
                            'name': f"{journal.name} [{prefix}]",
                            'status': 'corrupted',
                            'msg': _("Corrupted data on journal entry with id %s.", move.id),
                        })
                        hash_corrupted = True
                        break
                    previous_hash = move.inalterable_hash

                if not hash_corrupted:
                    results.append({
                        'name': f"{journal.name} [{prefix}]",
                        'status': 'verified',
                        'msg': _("Entries are correctly hashed"),
                        'from_name': build_move_info(moves[0])[0],
                        'from_hash': build_move_info(moves[0])[1],
                        'from_date': build_move_info(moves[0])[2],
                        'to_name': build_move_info(moves[-1])[0],
                        'to_hash': build_move_info(moves[-1])[1],
                        'to_date': build_move_info(moves[-1])[2],
                    })

        return {
            'results': results,
            'printing_date': format_date(self.env, fields.Date.to_string(fields.Date.context_today(self)))
        }
