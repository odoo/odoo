from odoo import fields, models, api
from odoo.tools import SQL


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_in_withhold_tax_amount = fields.Monetary(string="TDS Tax Amount", compute='_compute_withhold_tax_amount')
    l10n_in_tds_tcs_section_id = fields.Many2one(related="account_id.l10n_in_tds_tcs_section_id")
    l10n_in_suggested_tds_tcs_section_id = fields.Many2one(
        'l10n_in.section.alert',
        string="Suggested Section",
        compute='_compute_l10n_in_suggested_tds_tcs_section_id',
        store=True
    )

    @api.depends('tax_ids')
    def _compute_withhold_tax_amount(self):
        # Compute the withhold tax amount for the withholding lines
        withholding_lines = self.filtered('move_id.l10n_in_is_withholding')
        (self - withholding_lines).l10n_in_withhold_tax_amount = False
        for line in withholding_lines:
            line.l10n_in_withhold_tax_amount = line.currency_id.round(abs(line.price_total - line.price_subtotal))

    @api.depends('l10n_in_tds_tcs_section_id', 'price_total', 'parent_state', 'move_id.partner_id', 'move_id.l10n_in_withhold_move_ids')
    def _compute_l10n_in_suggested_tds_tcs_section_id(self):
        previous_lines = self.browse(self._get_lines_under_aggregate_limit())
        moves = (self | previous_lines).move_id
        for move in moves:
            sections = move._get_l10n_in_tds_tcs_applicable_sections()
            if not sections:
                move.invoice_line_ids.l10n_in_suggested_tds_tcs_section_id = False
                continue

            for section in sections:
                if not move._l10n_in_is_tds_tcs_applicable(section):
                    continue

                if section.tax_source_type == 'tds':
                    applicable_lines = move.invoice_line_ids.filtered(
                        lambda line: line.l10n_in_tds_tcs_section_id == section
                    )
                elif section.tax_source_type == 'tcs':
                    applicable_lines = move._get_tcs_applicable_lines(move.invoice_line_ids).filtered(
                        lambda line: line.l10n_in_tds_tcs_section_id == section
                    )
                else:
                    applicable_lines = False

                if applicable_lines:
                    applicable_lines.l10n_in_suggested_tds_tcs_section_id = section
                else:
                    move.invoice_line_ids.l10n_in_suggested_tds_tcs_section_id = False

    def _get_lines_under_aggregate_limit(self):
        lines = set()
        for move in self.mapped('move_id'):
            company_fiscalyear_dates = move.company_id.compute_fiscalyear_dates(move.date)
            fiscalyear_start_date = company_fiscalyear_dates['date_from']
            domain = [
                ('date', '>=', fiscalyear_start_date),
                '|',
                ('move_id.commercial_partner_id', 'in', self.mapped('move_id.commercial_partner_id.id')),
                ('move_id.commercial_partner_id.l10n_in_pan', 'in', self.mapped('move_id.commercial_partner_id.l10n_in_pan')),
                ('move_type', 'in', self.mapped('move_id.move_type')),
                ('parent_state', '=', 'posted'),
                ('l10n_in_suggested_tds_tcs_section_id', '=', False),
                ('l10n_in_tds_tcs_section_id', 'in', self.mapped('l10n_in_tds_tcs_section_id.id')),
                ('display_type', 'in', ('product', 'line_section', 'line_note')),
                ('move_id.country_code', '=', 'IN'),
            ]
            query = self.env['account.move.line']._where_calc(domain)
            result = self.env.execute_query_dict(SQL(
                    """
                    SELECT array_agg(account_move_line.id) as line_ids
                    FROM %s
                    WHERE %s
                    """,
                    query.from_clause,
                    query.where_clause)
                )
            line_ids = result[0].get('line_ids') if result else None
            if line_ids:
                lines.update(line_ids)
        return lines
