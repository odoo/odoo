from odoo import api, models, fields, _, Command
from odoo.tools import SQL
from odoo.tools.date_utils import get_month


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_in_is_withholding = fields.Boolean(
        string="Is Indian TDS Entry",
        copy=False,
        help="Technical field to identify Indian withholding entry"
    )
    l10n_in_withholding_ref_move_id = fields.Many2one(
        comodel_name='account.move',
        string="Indian TDS Ref Move",
        readonly=True,
        index='btree_not_null',
        copy=False,
        help="Reference move for withholding entry",
    )
    l10n_in_withhold_move_ids = fields.One2many(
        'account.move', 'l10n_in_withholding_ref_move_id',
        string="Indian TDS Entries"
    )
    l10n_in_withholding_line_ids = fields.One2many(
        'account.move.line', 'move_id',
        string="Indian TDS Lines",
        compute='_compute_l10n_in_withholding_line_ids',
    )
    l10n_in_total_withholding_amount = fields.Monetary(
        string="Total Indian TDS Amount",
        compute='_compute_l10n_in_total_withholding_amount',
        help="Total withholding amount for the move",
    )
    l10n_in_tcs_tds_warning = fields.Char('TDC/TCS Warning', compute="_compute_l10n_in_tcs_tds_warning")
    l10n_in_display_higher_tcs_button = fields.Boolean(string="Display higher TCS button", compute="_compute_l10n_in_display_higher_tcs_button")

    # === Compute Methods ===
    @api.depends('line_ids', 'l10n_in_is_withholding')
    def _compute_l10n_in_withholding_line_ids(self):
        # Compute the withholding lines for the move
        for move in self:
            if move.l10n_in_is_withholding:
                move.l10n_in_withholding_line_ids = move.line_ids.filtered('tax_ids')
            else:
                move.l10n_in_withholding_line_ids = False

    def _compute_l10n_in_total_withholding_amount(self):
        for move in self:
            move.l10n_in_total_withholding_amount = sum(move.l10n_in_withhold_move_ids.filtered(
                lambda m: m.state == 'posted').l10n_in_withholding_line_ids.mapped('l10n_in_withhold_tax_amount'))

    def _get_l10n_in_invalid_tax_lines(self):
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

    @api.depends('invoice_line_ids.tax_ids', 'commercial_partner_id.l10n_in_pan')
    def _compute_l10n_in_warning(self):
        super()._compute_l10n_in_warning()
        for move in self:
            warnings = move.l10n_in_warning or {}
            lines = move._get_l10n_in_invalid_tax_lines()
            if lines:
                warnings['lower_tcs_tax'] = {
                        'message': _("As the Partner's PAN missing/invalid apply TCS at the higher rate."),
                        'action_text': _("View Journal Items(s)"),
                        'action': lines._get_records_action(
                            name=_("Journal Items(s)"),
                            target='current',
                            views=[(self.env.ref("l10n_in_withholding.view_move_line_tree_l10n_in").id, "list")],
                            domain=[('id', 'in', lines.ids)]
                        )
                }
                move.l10n_in_warning = warnings

    def action_l10n_in_apply_higher_tax(self):
        self.ensure_one()
        invalid_lines = self._get_l10n_in_invalid_tax_lines()
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

    @api.depends('l10n_in_warning')
    def _compute_l10n_in_display_higher_tcs_button(self):
        for move in self:
            move.l10n_in_display_higher_tcs_button = (
                move.l10n_in_warning
                and move.l10n_in_warning.get('lower_tcs_tax')
            )

    def action_l10n_in_withholding_entries(self):
        self.ensure_one()
        return {
            'name': "TDS Entries",
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.l10n_in_withhold_move_ids.ids)],
        }

    def _get_sections_aggregate_sum_by_pan(self, section_alert, commercial_partner_id):
        self.ensure_one()
        month_start_date, month_end_date = get_month(self.date)
        company_fiscalyear_dates = self.company_id.sudo().compute_fiscalyear_dates(self.date)
        fiscalyear_start_date, fiscalyear_end_date = company_fiscalyear_dates['date_from'], company_fiscalyear_dates['date_to']
        default_domain = [
            ('account_id.l10n_in_tds_tcs_section_id', '=', section_alert.id),
            ('move_id.move_type', '!=', 'entry'),
            ('company_id', 'child_of', self.company_id.root_id.id),
            ('parent_state', '=', 'posted')
        ]
        if commercial_partner_id.l10n_in_pan:
            default_domain += [('move_id.commercial_partner_id.l10n_in_pan', '=', commercial_partner_id.l10n_in_pan)]
        else:
            default_domain += [('move_id.commercial_partner_id', '=', commercial_partner_id.id)]
        frequency_domains = {
            'monthly': [('date', '>=', month_start_date), ('date', '<=', month_end_date)],
            'fiscal_yearly': [('date', '>=', fiscalyear_start_date), ('date', '<=', fiscalyear_end_date)],
        }
        aggregate_result = {}
        for frequency, frequency_domain in frequency_domains.items():
            query = self.env['account.move.line']._where_calc(default_domain + frequency_domain)
            result = self.env.execute_query_dict(SQL(
                """
                SELECT COALESCE(sum(account_move_line.balance), 0) as balance,
                       COALESCE(sum(account_move_line.price_total * am.invoice_currency_rate), 0) as price_total
                  FROM %s
                  JOIN account_move AS am ON am.id = account_move_line.move_id
                 WHERE %s
                """,
                query.from_clause,
                query.where_clause)
            )
            aggregate_result[frequency] = result[0]
        return aggregate_result

    def _l10n_in_is_warning_applicable(self, section_id):
        self.ensure_one()
        match section_id.tax_source_type:
            case 'tcs':
                return self.journal_id.type == 'sale'
            case 'tds':
                return (
                    self.journal_id.type == 'purchase'
                    and section_id not in self.l10n_in_withhold_move_ids.filtered(lambda m:
                        m.state == 'posted'
                    ).mapped('line_ids.tax_ids.l10n_in_section_id')
                )
            case _:
                return False

    @api.depends('invoice_line_ids.price_total')
    def _compute_l10n_in_tcs_tds_warning(self):
        def _group_by_section_alert(invoice_lines):
            group_by_lines = {}
            for line in invoice_lines:
                group_key = line.account_id.sudo().l10n_in_tds_tcs_section_id
                if group_key and not line.company_currency_id.is_zero(line.price_total):
                    group_by_lines.setdefault(group_key, [])
                    group_by_lines[group_key].append(line)
            return group_by_lines

        def _is_section_applicable(section_alert, threshold_sums, invoice_currency_rate, lines):
            lines_total = sum(
                    (line.price_total * invoice_currency_rate) if section_alert.consider_amount == 'total_amount' else line.balance
                    for line in lines
                )
            if section_alert.is_aggregate_limit:
                aggregate_period_key = section_alert.consider_amount == 'total_amount' and 'price_total' or 'balance'
                aggregate_total = threshold_sums.get(section_alert.aggregate_period, {}).get(aggregate_period_key)
                if move.state == 'draft':
                    aggregate_total += lines_total
                if aggregate_total > section_alert.aggregate_limit:
                    return True
            return (
                section_alert.is_per_transaction_limit
                and lines_total > section_alert.per_transaction_limit
            )

        for move in self:
            if move.country_code == 'IN' and move.move_type in ['in_invoice', 'out_invoice']:
                warning = set()
                commercial_partner_id = move.commercial_partner_id
                existing_section = (self.l10n_in_withhold_move_ids.line_ids + move.line_ids).tax_ids.l10n_in_section_id
                for section_alert, lines in _group_by_section_alert(move.invoice_line_ids).items():
                    if (
                        (section_alert not in existing_section
                        or [line for line in lines if section_alert not in line.tax_ids.l10n_in_section_id])
                        and move._l10n_in_is_warning_applicable(section_alert)
                        and _is_section_applicable(
                            section_alert,
                            move._get_sections_aggregate_sum_by_pan(
                                section_alert,
                                commercial_partner_id
                            ),
                            move.invoice_currency_rate,
                            lines
                        )
                    ):
                        warning.add(section_alert.id)
                warning_sections = self.env['l10n_in.section.alert'].browse(warning)
                if warning_sections:
                    move.l10n_in_tcs_tds_warning = warning_sections._get_warning_message()
                else:
                    move.l10n_in_tcs_tds_warning = False
            else:
                move.l10n_in_tcs_tds_warning = False
