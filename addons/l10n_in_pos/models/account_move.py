# Part of Odoo. See LICENSE file for full copyright and licensing details.
from contextlib import contextmanager

from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('pos_session_ids', 'reversed_pos_order_id')
    def _compute_l10n_in_state_id(self):
        res = super()._compute_l10n_in_state_id()
        to_compute = self.filtered(lambda m: m.country_code == 'IN' and not m.l10n_in_state_id and m.journal_id.type == 'general' and (m.pos_session_ids or m.reversed_pos_order_id))
        for move in to_compute:
            move.l10n_in_state_id = move.company_id.state_id
        return res

    def _get_sync_stack(self, invoice_container, tax_container, misc_container):
        stack = super()._get_sync_stack(invoice_container, tax_container, misc_container)
        stack.append((9, self._sync_l10n_in_pos_gstr_section(misc_container)))
        return stack

    @contextmanager
    def _sync_l10n_in_pos_gstr_section(self, container):
        yield
        for entry in container['records']:
            # we set the section on the invoice lines
            entry.line_ids._set_l10n_in_gstr_section()
