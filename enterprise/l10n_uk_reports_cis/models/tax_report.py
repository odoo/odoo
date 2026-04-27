from odoo import models, _
from odoo.tools import SQL, float_round


class AccountTaxReportHandler(models.AbstractModel):
    _inherit = 'account.tax.report.handler'

    def _get_vat_closing_entry_additional_domain(self):
        purchase_tax_tags = self.env.ref('l10n_uk_reports_cis.account_uk_cis_report_line_purchase_expr_deduction')._get_matching_tags()
        sales_tax_tags = self.env.ref('l10n_uk_reports_cis.account_uk_cis_report_line_sale_expr_deduction')._get_matching_tags()
        tags = purchase_tax_tags + sales_tax_tags

        # EXTENDS account_reports
        domain = super()._get_vat_closing_entry_additional_domain()
        domain += [
            ('tax_tag_ids', 'not in', tags.ids),  # Exclude CIS taxes lines from tax closing.
        ]
        return domain


class BritishCISTaxReportCustomHandler(models.AbstractModel):
    _name = 'cis.tax.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'British Tax Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options)
        options['ignore_totals_below_sections'] = True

        options['buttons'] = [button for button in options['buttons'] if button['action'] != 'action_periodic_vat_entries']
        if self.env.user.has_group('account.group_account_manager'):
            options['buttons'].append({'name': _("Send to HMRC"), 'sequence': 40, 'action': 'action_open_monthly_return_wizard', 'always_show': True})
            options['buttons'].append({'name': _("Refresh HMRC request"), 'sequence': 40, 'action': 'action_refresh_hmrc_request'})

        purchase_base_tags = self.env.ref('l10n_uk_reports_cis.account_uk_cis_report_line_purchase_expr_base')._get_matching_tags()
        sales_base_tags = self.env.ref('l10n_uk_reports_cis.account_uk_cis_report_line_sale_expr_base')._get_matching_tags()
        tags = purchase_base_tags + sales_base_tags

        # We need to test on base tags instead of tax tags because the gross tax does not create a line.
        options['forced_domain'] = [*options.get('forced_domain', []), ('move_id.line_ids.tax_ids.repartition_line_ids.tag_ids', 'in', tags.ids)]

    def _report_custom_engine_cis_materials_purchase(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        report = self.env['account.report'].browse(options['report_id'])
        purchase_base_tags = self.env.ref('l10n_uk_reports_cis.account_uk_cis_report_line_purchase_expr_base')._get_matching_tags()
        domain = f"[('display_type', '=', 'product'), ('move_id.move_type', 'in', ('in_invoice', 'in_refund')), ('tax_tag_ids', 'not in', {purchase_base_tags.ids})]"
        result = report._compute_formula_batch_with_engine_domain(options, 'strict_range', {domain: expressions}, current_groupby, next_groupby, offset, limit, warnings)
        return result[domain, expressions]

    def _report_custom_engine_cis_materials_sales(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        report = self.env['account.report'].browse(options['report_id'])
        sales_base_tags = self.env.ref('l10n_uk_reports_cis.account_uk_cis_report_line_sale_expr_base')._get_matching_tags()
        domain = f"[('display_type', '=', 'product'), ('move_id.move_type', 'in', ('out_invoice', 'out_refund')), ('tax_tag_ids', 'not in', {sales_base_tags.ids})]"
        result = report._compute_formula_batch_with_engine_domain(options, 'strict_range', {domain: expressions}, current_groupby, next_groupby, offset, limit, warnings)
        return result[domain, expressions]

    def _custom_line_postprocessor(self, report, options, lines):
        for column_index, column in enumerate(options['columns']):
            if column['expression_label'] in ('payment', 'materials'):
                for line in lines:
                    column_dict = line['columns'][column_index]
                    value = float_round(column_dict['no_format'], precision_digits=0, rounding_method='DOWN')
                    line['columns'][column_index] = report._build_column_dict(value, column)

        return lines

    def _customize_warnings(self, report, options, all_column_groups_expression_totals, warnings):
        queries = []
        for column_group in all_column_groups_expression_totals:
            column_group_options = report._get_column_group_options(options, column_group)
            queries.append(
                SQL(
                    """
                    SELECT
                    COALESCE(
                        ARRAY_AGG(DISTINCT move.partner_id),
                        '{}'
                    ) AS unregistered_partners
                    FROM account_move move
                    WHERE move.l10n_uk_cis_inactive_partner = TRUE
                    AND move.date >= %(period_start)s
                    AND move.date <= %(period_end)s
                    """,
                    period_start=column_group_options['date']['date_from'],
                    period_end=column_group_options['date']['date_to'],
                )
            )

        self._cr.execute(SQL(" UNION ALL ").join(queries))
        result = self._cr.dictfetchall()
        unregistered_partners = list({
            id for column_group_result in result
            for id in column_group_result['unregistered_partners']
        })

        if unregistered_partners:
            warnings['l10n_uk_reports_cis.warning_cis_unregistered_partner'] = {
                'partner_ids': unregistered_partners,
                'alert_type': 'warning'
            }

    def action_open_monthly_return_wizard(self, options):
        context = self.env.context.copy()
        context.update({'options': options})
        return {
            'type': 'ir.actions.act_window',
            'name': _("CIS monthly return"),
            'view_mode': 'form',
            'res_model': 'cis.monthly.return.wizard',
            'target': 'new',
            'context': context,
            'views': [[False, 'form']],
        }

    def action_refresh_hmrc_request(self, options):
        self.env.ref('l10n_uk_hmrc.ir_cron_l10n_uk_hmrc_process_transactions')._trigger()
        return {'type': 'ir.actions.act_window_close'}

    def action_open_partners_view_with_unregistered_cis(self, options, params=None):
        partner_ids = params.get('partner_ids')
        partners = self.env['res.partner'].browse(partner_ids)
        name = _("Unregistered partners") if len(partners) > 1 else _("Unregistered partner")
        return partners._get_records_action(name=name)
