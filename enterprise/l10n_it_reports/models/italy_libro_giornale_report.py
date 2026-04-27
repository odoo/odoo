from datetime import date
from odoo import api, models, _
from odoo.tools import groupby


class LibroGiornaleReportHandler(models.AbstractModel):
    _name = 'l10n_it.libro_giornale.report.handler'
    _inherit = 'account.journal.report.handler'
    _description = 'Libro Giornale Report Handler'

    def _get_custom_display_config(self):
        display_config = super()._get_custom_display_config()
        if self.env.ref('l10n_it_reports.libro_giornale_pdf', raise_if_not_found=False):
            display_config['pdf_export']['pdf_export_main'] = 'l10n_it_reports.libro_giornale_pdf'
        return display_config

    def _get_base_line(self, report, options, export_type, document, line_entry, line_index, even, has_taxes):
        """Modify base line data for the report"""

        line = super()._get_base_line(report, options, export_type, document, line_entry, line_index, even, has_taxes)

        line.update({
            "date": {'data': line_entry['date']},
            "line_number": {'data': line_index + 1},
            "journal_entry": {'data': line_entry['move_name']},
            "account_name": {'data': line_entry['account_name']},
            "display_type": {'data': line_entry['display_type']},
            "credit_float": line_entry['credit'],
            "debit_float": line_entry['debit'],
            "journal_id": line_entry['journal_id']
        })

        return line

    def _get_columns_for_journal(self, journal, export_type='pdf'):
        # Update columns
        columns = [
            {'name': _('Document'), 'label': 'document'},
            {'name': _('Line'), 'label': 'line_number', 'class': 'o_right_alignment'},
            {'name': _('Account Code'), 'label': 'account_code', 'class': 'o_fixed_column_width'},
            {'name': _('Account Name'), 'label': 'account_name', 'class': 'o_overflow_name'},
            {'name': _('Name'), 'label': 'name', 'class': 'o_overflow_name'},
            {'name': _('Debit'), 'label': 'debit', 'class': 'o_right_alignment'},
            {'name': _('Credit'), 'label': 'credit', 'class': 'o_right_alignment'}
        ]

        return columns

    def _generate_document_data_for_export(self, report, options, export_type='pdf'):
        data = super()._generate_document_data_for_export(report, options, export_type)
        journals_vals = data.get('journals_vals', [])

        if not journals_vals:
            return {'journals_vals': [], 'global_tax_summary': False}

        libro_giornale_data = self.build_libro_giornale_data(journals_vals)
        sorted_lines = self.sort_libro_giornale_lines(libro_giornale_data['lines'])

        libro_giornale_data['lines'] = self._post_process_sorted_libro_giornale_lines(sorted_lines)

        total_credit, total_debit = self.calculate_totals(libro_giornale_data['lines'])
        libro_giornale_data['lines'].append({
            'name': {'data': _('Total')},
            'debit': {'data': report._format_value(options, total_debit, 'monetary')},
            'credit': {'data': report._format_value(options, total_credit, 'monetary')}
        })

        if "tax_summary" in libro_giornale_data:
            del libro_giornale_data["tax_summary"]

        return {
            'journals_vals': [libro_giornale_data],
            'global_tax_summary': False
        }

    def build_libro_giornale_data(self, journals_vals):
        """Flatten journal lines into a single Libro Giornale report structure."""
        all_lines = [
            line for journal_vals in journals_vals
            for line in journal_vals.get('lines', [])
            if line.get('account_code')
        ]

        return {
            "name": "Libro Giornale",
            "lines": all_lines,
            "columns": journals_vals[0]['columns']
        }

    def sort_libro_giornale_lines(self, lines):
        """
            Sort lines by journal_id, date, entry name, and display type.
            Sorting priority:
            1. journal_id (default: 10000 if missing)
            2. date (handled by safe_date function)
            3. journal_entry name (entry['journal_entry']['data'])
            4. display_type order (using display_type_order mapping, default: 99) product then tax then payment term
            """
        def safe_date(entry):
            """Return a valid date or a fallback far in the future."""
            date_value = entry.get('date', {}).get('data')
            return date_value if isinstance(date_value, date) else date(9999, 12, 31)

        display_type_order =  {
            'product': 1,
            'tax': 2,
            'payment_term': 3,
        }

        return sorted(
            lines,
            key=lambda entry: (
                entry.get('journal_id', 10000),
                safe_date(entry),
                entry.get('journal_entry', {}).get('data'),
                display_type_order.get(entry.get('display_type',{}).get('data'), 99)
            )
        )

    def calculate_totals(self, lines):
        """Calculate the total debit and credit of all lines."""
        total_credit = sum(line.get('credit_float', 0.0) for line in lines)
        total_debit = sum(line.get('debit_float', 0.0) for line in lines)
        return total_credit, total_debit

    def _custom_line_postprocessor(self, report, options, lines):
        """Post-process report lines (e.g., remove global tax summary)"""
        report_lines = super()._custom_line_postprocessor(report, options, lines)
        report_lines_tax_free = [
            line for line in report_lines
            if "tax_report_section" not in report._get_markup(line['id'])
        ]
        return report_lines_tax_free

    def _should_use_bank_journal_export(self, journal_vals):
        return False

    @api.model
    def _post_process_sorted_libro_giornale_lines(self, lines):
        """
            Perform post-processing on sorted lines.
            - Assigns alternating line classes based on journal_entry groups.
            - Sets 'document.data' for the first and last lines of each group.
            Assigns sequential 'line_number' if 'account_name' is present.
        """
        if not lines:
            return

        is_odd = True
        line_number = 1

        # Group lines by journal_entry
        for move, move_lines in groupby(lines, key=lambda l: l.get('journal_entry', {}).get('data')):
            for i, line in enumerate(move_lines):
                # Assign line class
                line['line_class'] = 'o_odd' if is_odd else 'o_even'

                if 'account_name' in line:
                    line['line_number'] = {'data': line_number}
                    line_number += 1

                # Custom logic for the first two lines in the group
                if len(move_lines) > 1:
                    if i == 0:
                        line['document'] = {
                            'data': line.get('journal_entry', {}).get('data'),
                            'class': 'o_bold'
                        }
                    elif i == 1:
                        line['document'] = {
                            'data': line.get('date', {}).get('data'),
                        }
                    else:
                        line['document'] = {}

            is_odd = not is_odd

        return lines
