from odoo import models, _
from odoo.tools import SQL
from odoo.tools.date_utils import get_month


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _l10n_in_get_sections_aggregate_sum_by_pan(self, section_alert, commercial_partner_id):
        self.ensure_one()
        month_start_date, month_end_date = get_month(self.date)
        company_fiscalyear_dates = self.company_id.compute_fiscalyear_dates(self.date)
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

    def _l10n_in_get_section_warning_message(self, sections, applicable_lines):
        return {
            'message': sections._get_warning_message(),
            'action_text': _("View Journal Items(s)"),
            'action': {
                'type': 'ir.actions.act_window',
                'name': _('Journal Items(s)'),
                'res_model': 'account.move.line',
                'domain': [('id', 'in', applicable_lines.ids)],
                'views': [(self.env.ref('l10n_in_withholding_suggestion.view_move_line_list_l10n_in_withholding_suggestion').id, 'list')],
                'context': {
                    'default_tax_type_use': self.invoice_filter_type_domain,
                    'move_type': self.move_type == 'in_invoice'
                },
            }
        }

    def _l10n_in_get_applicable_sections(self, existing_section):
        def _group_by_section_alert(invoice_lines):
            group_by_lines = {}
            for line in invoice_lines:
                group_key = line.account_id.l10n_in_tds_tcs_section_id
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
                if self.state == 'draft':
                    aggregate_total += lines_total
                if aggregate_total > section_alert.aggregate_limit:
                    return True
            return (
                section_alert.is_per_transaction_limit
                and lines_total > section_alert.per_transaction_limit
            )

        warning = set()
        for section_alert, lines in _group_by_section_alert(self.invoice_line_ids).items():
            if (
                (section_alert not in existing_section
                or self._l10n_in_get_applicable_lines(lines))
                and self._l10n_in_is_warning_applicable(section_alert)
                and _is_section_applicable(
                    section_alert,
                    self._l10n_in_get_sections_aggregate_sum_by_pan(
                        section_alert,
                        self.commercial_partner_id
                    ),
                    self.invoice_currency_rate,
                    lines
                )
            ):
                warning.add(section_alert.id)
        return self.env['l10n_in.section.alert'].browse(warning)

    def _l10n_in_get_applicable_lines(self, lines):
        applicable_lines = set()
        for line in lines:
            if line.l10n_in_tds_tcs_section_id not in line.tax_ids.l10n_in_section_id:
                applicable_lines.add(line.id)
        return self.env['account.move.line'].browse(applicable_lines)
