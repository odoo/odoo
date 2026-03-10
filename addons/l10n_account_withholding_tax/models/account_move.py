from odoo import api, fields, models, Command
from odoo.tools import SQL
from odoo.tools.date_utils import get_month


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_withholding_ref_move_id = fields.Many2one(
        comodel_name='account.move',
        string="Withhold Ref Move",
        readonly=True,
        index='btree_not_null',
        copy=False,
        help="Reference move for withholding entry",
    )
    l10n_withholding_move_ids = fields.One2many(
        'account.move', 'l10n_withholding_ref_move_id',
        string="Withhold Entries"
    )
    l10n_withholding_line_ids = fields.One2many(
        'account.move.line', 'move_id',
        string="Withholding Lines",
        compute='_compute_l10n_withholding_line_ids',
    )
    l10n_total_withholding_amount = fields.Monetary(
        string="Total Withholding Tax Amount",
        compute='_compute_l10n_total_withholding_amount',
        help="Total withholding amount for the move",
    )
    l10n_withholding_applicable_section_names = fields.Char(compute='_compute_withholding_applicable_section_names')
    withhold_only_on_payment = fields.Boolean(
        string="Withhold on Payment",
        help="Indicates whether the withholding tax is applied on payment or on invoice.",
        compute='_compute_withhold_only_on_payment',
    )

    @api.depends('company_id.withhold_applicable_on')
    def _compute_withhold_only_on_payment(self):
        for move in self:
            move.withhold_only_on_payment = move.company_id.withhold_applicable_on == 'payment'

    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.l10n_total_withholding_amount:
            return 'l10n_account_withholding_tax.report_invoice_document'
        return super()._get_name_invoice_report()

    def _compute_payments_widget_reconciled_info(self):
        """Add withhold field in the reconciled vals to be able to show the payment method in the invoice."""
        super()._compute_payments_widget_reconciled_info()
        for move in self:
            if move.invoice_payments_widget:
                payments_widget = move.invoice_payments_widget
                if move.state == 'posted' and move.is_invoice(include_receipts=True):
                    reconciled_partials = move._get_all_reconciled_invoice_partials()
                    for i, reconciled_partial in enumerate(reconciled_partials):
                        if reconciled_partial['aml'].is_withhold_line:
                            payments_widget['content'][i].update({
                                'is_withhold_line': True,
                            })
                        else:
                            payments_widget['content'][i].update({
                                'is_withhold_line': False,
                            })
                payments_widget['is_withhod_move'] = bool(move.l10n_total_withholding_amount)
                move.invoice_payments_widget = payments_widget

    def _get_withhold_account_by_sum(self):
        withhold_data = {}
        for line in self.invoice_line_ids:
            if line.account_id.withholding_tax_section_id.tax_ids:
                if line.account_id not in withhold_data:
                    withhold_data[line.account_id] = 0.0
                withhold_data[line.account_id] += line.price_subtotal

        for line in self.l10n_withholding_move_ids.line_ids:
            if line.account_id in withhold_data:
                withhold_data[line.account_id] -= line.price_subtotal

        return withhold_data

    @api.depends('line_ids')
    def _compute_l10n_withholding_line_ids(self):
        # Compute the withholding lines for the move
        for move in self:
            move.l10n_withholding_line_ids = move.line_ids.filtered('tax_ids')

    @api.depends('l10n_withholding_line_ids')
    def _compute_l10n_total_withholding_amount(self):
        for move in self:
            move.l10n_total_withholding_amount = sum(move.l10n_withholding_move_ids.filtered(
                lambda m: m.state == 'posted').l10n_withholding_line_ids.mapped('l10n_withholding_tax_amount'))

    def action_l10n_withholding_entries(self):
        self.ensure_one()
        return {
            'name': "Withholding Entries",
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.l10n_withholding_move_ids.ids)],
            'context': {'create': False},
        }

    @api.depends('invoice_line_ids.price_total', 'commercial_partner_id')
    def _compute_withholding_applicable_section_names(self):
        for move in self:
            move.l10n_withholding_applicable_section_names = False
            if applicable_sections := move._get_withholding_applicable_sections():
                move.l10n_withholding_applicable_section_names = ", ".join(applicable_sections.mapped('name'))

    def _get_sections_aggregate_sum(self, commercial_partner_id):
        self.ensure_one()
        month_start_date, month_end_date = get_month(self.date)
        company_fiscalyear_dates = self.company_id.sudo().compute_fiscalyear_dates(self.date)
        fiscalyear_start_date = company_fiscalyear_dates['date_from']
        fiscalyear_end_date = company_fiscalyear_dates['date_to']

        default_domain = [
            ('move_id.move_type', '!=', 'entry'),
            ('parent_state', '=', 'posted'),
            ('move_id.commercial_partner_id', '=', commercial_partner_id.id),
        ]

        frequency_domains = {
            'monthly': [
                ('date', '>=', month_start_date),
                ('date', '<=', month_end_date)
            ],
            'fiscal_yearly': [
                ('date', '>=', fiscalyear_start_date),
                ('date', '<=', fiscalyear_end_date)
            ],
        }
        aggregate_result = {}
        for frequency, frequency_domain in frequency_domains.items():
            query = self.env['account.move.line']._search(
                default_domain + frequency_domain,
                bypass_access=True,
                active_test=False
            )

            result = self.env.execute_query_dict(SQL(
                """
                SELECT COALESCE(sum(account_move_line.balance), 0) as balance,
                    COALESCE(sum(account_move_line.price_total * am.invoice_currency_rate), 0) as price_total
                FROM %s
                JOIN account_move AS am ON am.id = account_move_line.move_id
                WHERE %s
                """,
                query.from_clause,
                query.where_clause
            ))
            aggregate_result[frequency] = result[0]
        return aggregate_result

    def _get_withholding_applicable_sections(self):
        def _group_by_section_alert(invoice_lines):
            group_by_lines = {}
            for line in invoice_lines:
                group_key = line.account_id.withholding_tax_section_id
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
                aggregate_total += lines_total
                if aggregate_total > section_alert.aggregate_limit:
                    return True
            return (
                section_alert.is_per_transaction_limit
                and lines_total > section_alert.per_transaction_limit
            )

        if self.move_type in ['in_invoice', 'out_invoice']:
            warning = set()
            existing_section = self.reconciled_payment_ids.withholding_line_ids.tax_id.withholding_tax_section_id or (
                self.l10n_withholding_move_ids.line_ids + self.line_ids
            ).tax_ids.withholding_tax_section_id
            for section_alert, lines in _group_by_section_alert(self.invoice_line_ids).items():
                if (
                    section_alert not in existing_section
                    and _is_section_applicable(
                        section_alert,
                        self._get_sections_aggregate_sum(self.commercial_partner_id),
                        self.invoice_currency_rate,
                        lines
                    )
                ):
                    warning.add(section_alert.id)
            return self.env['account.withholding.tax.section'].browse(warning)

    def _reverse_moves(self, default_values_list=None, cancel=False):
        """ Override to set the withholding reference move on the reversed move. """
        reverse_moves = super()._reverse_moves(default_values_list=default_values_list, cancel=cancel)
        if self.l10n_withholding_ref_move_id:
            reverse_moves.write({'l10n_withholding_ref_move_id': self.l10n_withholding_ref_move_id.id})
        return reverse_moves

    def get_withholding_lines(self):
        section_map = {}

        for line in self.line_ids:
            if line.display_type != 'product':
                continue

            section = line.account_id.withholding_tax_section_id
            if not section:
                continue

            values = section_map.setdefault(section, {
                'base_amount': 0.0,
                'analytic_distribution': {},
            })

            values['base_amount'] += line.amount_residual

            if line.analytic_distribution:
                analytic_dist = values['analytic_distribution']
                for analytic_id, percentage in line.analytic_distribution.items():
                    analytic_dist[analytic_id] = analytic_dist.get(analytic_id, 0.0) + percentage

        commands = [Command.clear()]

        for section, values in section_map.items():
            taxes = section.tax_ids
            if not taxes:
                continue

            tax = taxes.sorted('sequence')[0]

            commands.append(Command.create({
                'tax_id': tax.id,
                'analytic_distribution': values['analytic_distribution'],
            }))

        return commands
