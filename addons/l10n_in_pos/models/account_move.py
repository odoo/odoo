# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo import api, models
from odoo.tools import SQL

# Format of l10n_in_b2c_invoice_number, see pos.order._l10n_in_format_b2c_invoice_number
B2C_INVOICE_NUMBER_REGEX = r'^[A-Z][0-9]{2}/[0-9]{4}/[0-9]{7}$'


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('pos_session_ids', 'reversed_pos_order_id')
    def _compute_l10n_in_state_id(self):
        res = super()._compute_l10n_in_state_id()
        to_compute = self.filtered(lambda m: m.country_code == 'IN' and not m.l10n_in_state_id and m.journal_id.type == 'sale' and (m.pos_session_ids or m.reversed_pos_order_id))
        for move in to_compute:
            move.l10n_in_state_id = move.company_id.state_id
        return res

    def _get_last_sequence_domain(self, relaxed=False):
        # B2C PoS invoices share the journal, the other invoices must keep the journal series.
        condition = super()._get_last_sequence_domain(relaxed)
        if self.country_code == 'IN' and self.journal_id.type == 'sale':
            condition = SQL("%s AND name !~ %s", condition, B2C_INVOICE_NUMBER_REGEX)
        return condition

    @api.model
    def _deduce_sequence_number_reset(self, name):
        # The PoS identifier of a B2C invoice number (e.g. P26/2101/0000001) is not a year.
        if len(self) == 1 and self.country_code == 'IN' and name and re.fullmatch(B2C_INVOICE_NUMBER_REGEX, name):
            if name == self.name:
                return 'never'
            name = self._get_starting_sequence()
        return super()._deduce_sequence_number_reset(name)

    def _l10n_in_detach_payment_lines(self):
        self.ensure_one()
        term_lines = self.line_ids.filtered(lambda line: line.display_type == 'payment_term')
        payment_lines = term_lines.matched_debit_ids.debit_move_id | term_lines.matched_credit_ids.credit_move_id
        term_lines.remove_move_reconcile()
        return payment_lines
