from odoo import fields, models, _
from odoo.tools import SQL


class AccountFollowupCustomHandler(models.AbstractModel):
    _name = 'account.followup.report.handler'
    _inherit = 'account.partner.ledger.report.handler'
    _description = 'Follow-Up Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        options['hide_initial_balance'] = True
        if len(options['partner_ids']) == 1:
            options['ignore_totals_below_sections'] = True
            options['hide_partner_totals'] = True

        if options['report_id'] != previous_options.get('report_id') and options['export_mode'] != 'print':
            options['unreconciled'] = True
            # by default, select only the 'sales' journals
            for journal in options.get('journals', []):
                journal['selected'] = journal.get('type') != 'general'  # dividers don't get a type
            # Since we forced the selection of some journal, we need to recompute the filter label
            report._init_options_journals_names(options, previous_options=previous_options)

    def _get_custom_display_config(self):
        display_config = super()._get_custom_display_config()
        if self.env.ref('account_reports.pdf_export_main_customer_report', raise_if_not_found=False):
            display_config.setdefault('pdf_export', {})['pdf_export_main'] = 'account_reports.pdf_export_main_customer_report'
        return display_config

    def _filter_overdue_amls_from_results(self, aml_results):
        return list(filter(lambda aml: aml['date_maturity'] and aml['date_maturity'] < fields.Date.today(), aml_results))

    def _filter_due_amls_from_results(self, aml_results):
        return list(filter(lambda aml: not aml['date_maturity'] or aml['date_maturity'] >= fields.Date.today(), aml_results))

    def _get_partner_aml_report_lines(self, report, options, partner_line_id, aml_results, progress, offset=0, level_shift=0):

        def create_status_line(status_name):
            return {
                'id': report._get_generic_line_id(None, None, markup=status_name, parent_line_id=partner_line_id),
                'name': status_name,
                'level': 3 + level_shift,
                'parent_id': partner_line_id,
                'columns': [{} for _col in options['columns']],
                'unfolded': True,
            }

        def get_aml_lines_with_status_line(status_name, status_line_id, aml_values, treated_results_count, progress):
            lines = []
            next_progress = progress
            has_more = False

            if not status_line_id or offset == 0:
                status_line = create_status_line(status_name)
                lines.append(status_line)
                status_line_id = status_line['id']

            for aml_value in aml_values:
                if self._is_report_limit_reached(report, options, treated_results_count):
                    # We loaded one more than the limit on purpose: this way we know we need a "load more" line
                    has_more = True
                    break

                aml_report_line = self._get_report_line_move_line(options, aml_value, status_line_id, next_progress, level_shift=level_shift + 1)
                lines.append(aml_report_line)
                next_progress = self._init_load_more_progress(options, aml_report_line)
                treated_results_count += 1

            return lines, next_progress, treated_results_count, has_more

        lines = []
        next_progress = progress
        has_more = False
        treated_results_count = 0
        due_line_id, overdue_line_id = self._get_unfolded_partner_status_lines(report, options, partner_line_id)

        overdue_aml_values = self._filter_overdue_amls_from_results(aml_results)
        due_aml_values = self._filter_due_amls_from_results(aml_results)

        if overdue_aml_values:
            overdue_lines, next_progress, treated_results_count, has_more = get_aml_lines_with_status_line(_('Overdue'), overdue_line_id, overdue_aml_values, treated_results_count, next_progress)
            lines.extend(overdue_lines)
            # If we reached the limit just before the due line and have already loaded one extra line, we should skip the due line for now and add a "load more" line
            if self._is_report_limit_reached(report, options, treated_results_count) and due_aml_values:
                has_more = True

        if due_aml_values and not has_more:
            due_lines, next_progress, treated_results_count, has_more = get_aml_lines_with_status_line(_('Due'), due_line_id, due_aml_values, treated_results_count, next_progress)
            lines.extend(due_lines)

        return lines, next_progress, treated_results_count, has_more

    def _get_unfolded_partner_status_lines(self, report, options, partner_line_id):
        _dummy1, _dummy2, partner_id = report._parse_line_id(partner_line_id)[-1]
        due_line_id, overdue_line_id = None, None
        for line_id in options['unfolded_lines']:
            res_ids_map = report._get_res_ids_from_line_id(line_id, ['account.report', 'res.partner'])
            if 'res.partner' in res_ids_map and res_ids_map['account.report'] == report.id and res_ids_map['res.partner'] == partner_id:
                markup, _dummy1, _dummy2 = report._parse_line_id(line_id)[-1]
                if markup == 'Due':
                    due_line_id = line_id
                if markup == 'Overdue':
                    overdue_line_id = line_id
        return due_line_id, overdue_line_id

    def _get_order_by_aml_values(self):
        return SQL('account_move_line.date_maturity, %(order_by)s', order_by=super()._get_order_by_aml_values())
