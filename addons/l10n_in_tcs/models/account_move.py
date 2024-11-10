from odoo import api, models, fields, _, Command


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_in_display_higher_tcs_button = fields.Boolean(string="Display higher TCS button", compute="_compute_l10n_in_display_higher_tcs_button")

    @api.depends('l10n_in_warning')
    def _compute_l10n_in_display_higher_tcs_button(self):
        for move in self:
            move.l10n_in_display_higher_tcs_button = (
                move.l10n_in_warning
                and move.l10n_in_warning.get('lower_tcs_tax')
            )

    @api.depends('invoice_line_ids.tax_ids', 'commercial_partner_id.l10n_in_pan', 'invoice_line_ids.price_total')
    def _compute_l10n_in_warning(self):
        super()._compute_l10n_in_warning()
        for move in self:
            if move.country_code == 'IN' and move.move_type == 'out_invoice':
                warnings = move.l10n_in_warning or {}
                lines = move._l10n_in_get_invalid_tax_lines()
                existing_section = move.line_ids.tax_ids.l10n_in_section_id
                sections = move._l10n_in_get_applicable_sections(existing_section)
                if lines:
                    warnings['lower_tcs_tax'] = {
                        'message': _("As the Partner's PAN missing/invalid apply TCS at the higher rate."),
                        'action_text': _("View Journal Items(s)"),
                        'action': lines._get_records_action(
                            name=_("Journal Items(s)"),
                            target='current',
                            views=[(self.env.ref("l10n_in_tcs.view_move_line_tree_l10n_in_tcs").id, "list")],
                            domain=[('id', 'in', lines.ids)]
                        )
                    }
                if sections:
                    tcs_applicable_lines = self._l10n_in_get_applicable_lines(self.invoice_line_ids)
                    warnings['tcs_threshold_alert'] = self._l10n_in_get_section_warning_message(sections, tcs_applicable_lines)
                move.l10n_in_warning = warnings

    def action_l10n_in_apply_higher_tax(self):
        self.ensure_one()
        invalid_lines = self._l10n_in_get_invalid_tax_lines()
        for line in invalid_lines:
            updated_tax_ids = []
            for tax in line.tax_ids:
                if tax.l10n_in_section_id.tax_source_type == 'tcs':
                    max_tax = max(
                        tax.l10n_in_section_id.l10n_in_section_tax_ids,
                        key=lambda t: t.amount
                    )
                    updated_tax_ids.append(max_tax.id)
                else:
                    updated_tax_ids.append(tax.id)
            if set(line.tax_ids.ids) != set(updated_tax_ids):
                line.write({'tax_ids': [Command.clear()] + [Command.set(updated_tax_ids)]})

    def _l10n_in_get_invalid_tax_lines(self):
        self.ensure_one()
        if self.country_code == 'IN' and not self.commercial_partner_id.l10n_in_pan:
            lines = self.env['account.move.line']
            for line in self.invoice_line_ids:
                for tax in line.tax_ids:
                    if (
                        tax.l10n_in_section_id.tax_source_type == 'tcs'
                        and tax.amount != max(tax.l10n_in_section_id.l10n_in_section_tax_ids, key=lambda t: abs(t.amount)).amount
                    ):
                        lines |= line._origin
            return lines
