import json

from odoo import models
from odoo.exceptions import UserError


class AccountResequenceWizard(models.TransientModel):
    _inherit = 'account.resequence.wizard'

    def resequence(self):
        # EXTENDS account
        # Resequencing closes a gap left in an AT series by a deleted draft (see `account.move._l10n_pt_issue`).
        # Only invoices not issued yet can be renumbered, within their series and after its last
        # issued number; the series then continues from the highest number held.
        pt_moves = self.move_ids.filtered(lambda m: m._l10n_pt_country_ok() and m.l10n_pt_at_series_id)
        if not pt_moves:
            return super().resequence()
        if issued := pt_moves.filtered('l10n_pt_document_number'):
            raise UserError(self.env._(
                "Issued Portuguese invoices cannot be resequenced: %(invoices)s.",
                invoices=", ".join(issued.mapped('name')),
            ))
        new_values = json.loads(self.new_values)
        new_name_key = 'new_by_name' if self.ordering == 'keep' else 'new_by_date'
        # sudo: a series shared across branches holds invoices of companies the user may not see.
        moves_sudo = self.env['account.move'].sudo()
        last_issued_numbers = dict(moves_sudo._read_group(
            [('l10n_pt_at_series_id', 'in', pt_moves.l10n_pt_at_series_id.ids), ('l10n_pt_document_number', '!=', False)],
            groupby=['l10n_pt_at_series_id'],
            aggregates=['sequence_number:max'],
        ))
        for at_series, moves in pt_moves.grouped('l10n_pt_at_series_id').items():
            prefix = f"{at_series.document_identifier}/"
            new_names = [new_values[str(move.id)][new_name_key] for move in moves if str(move.id) in new_values]
            if wrong := [name for name in new_names if not name.startswith(prefix) or not name[len(prefix):].isdigit()]:
                raise UserError(self.env._(
                    "The invoices of the AT series %(series)s keep its numbering (%(prefix)s...): %(names)s.",
                    series=at_series.document_identifier,
                    prefix=prefix,
                    names=", ".join(wrong),
                ))
            last_issued = last_issued_numbers.get(at_series) or 0
            if min(int(name[len(prefix):]) for name in new_names) <= last_issued:
                raise UserError(self.env._(
                    "The invoices of the AT series %(series)s can only be renumbered after its last issued number, %(number)s.",
                    series=at_series.document_identifier,
                    number=last_issued,
                ))
        res = super(AccountResequenceWizard, self.with_context(l10n_pt_resequence=True)).resequence()
        last_held_numbers = dict(moves_sudo._read_group(
            [('l10n_pt_at_series_id', 'in', pt_moves.l10n_pt_at_series_id.ids), *moves_sudo._l10n_pt_numbered_domain()],
            groupby=['l10n_pt_at_series_id'],
            aggregates=['sequence_number:max'],
        ))
        for at_series in pt_moves.l10n_pt_at_series_id:
            # sudo: the series' number sequence is technical, users renumbering invoices cannot write it.
            at_series._l10n_pt_get_document_number_sequence().sudo().number_next = (last_held_numbers.get(at_series) or 0) + 1
        return res
