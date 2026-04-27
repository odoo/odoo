# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import re

import xlsxwriter

from odoo import _, models
from odoo.addons.account_reports.models.account_report import AccountReport
from odoo.tools import format_date, float_repr, SQL


class WT003ReportCustomHandler(models.AbstractModel):
    _name = 'l10n_kh.wt003.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'Form WT 003 Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options['buttons'].append({
            'name': _('WT 003 (XLSX)'),
            'sequence': 0,
            'action': 'export_file',
            'action_param': 'export_wt_003',
            'file_export_type': _('XLSX'),
        })

    def _get_wt_003_export_data(self, options):
        """ Fetches the information about tax invoice that will be used in order to build the export """
        def _format_number(number, currency):
            rounded_number = currency.round(number)
            return float_repr(rounded_number, precision_digits=currency.decimal_places)

        report = self.env.ref('l10n_kh.l10n_kh_wt003')
        ChartTemplate = self.env['account.chart.template'].with_company(self.env.company)
        currency = self.env.company.currency_id

        query = report._get_report_query(options, 'strict_range')
        query = SQL(
            """
            WITH tag_amounts_per_move AS (
                SELECT commercial_partner.name                              AS commercial_partner_name,
                       commercial_partner.vat                               AS commercial_partner_vat,
                       account_move_line__move_id.fiscal_position_id        AS fiscal_position_id,
                       CASE
                           WHEN payment.id IS NOT NULL THEN account_move_line__move_id.date
                           ELSE account_move_line__move_id.invoice_date
                           END                                              AS date,
                       CASE
                           WHEN payment.id IS NOT NULL THEN account_move_line__move_id.ref
                           ELSE account_move_line__move_id.name
                           END                                              AS name,
                       REGEXP_REPLACE(%(tag_name)s, '^[+-]', '')            AS tag_name,
                       SUM(
                           account_move_line.balance
                           * CASE WHEN account_move_line.tax_tag_invert THEN -1 ELSE 1 END
                           * CASE WHEN tag.tax_negate THEN -1 ELSE 1 END
                       )                                                    AS tag_amount
                 FROM %(table_references)s
                 JOIN account_account_tag_account_move_line_rel aml_tag ON account_move_line.id = aml_tag.account_move_line_id
                 JOIN account_account_tag tag ON aml_tag.account_account_tag_id = tag.id
                 JOIN res_partner commercial_partner ON commercial_partner.id = account_move_line__move_id.commercial_partner_id
            LEFT JOIN account_payment payment ON payment.move_id = account_move_line__move_id.id
                WHERE %(search_condition)s
                  AND %(tag_name)s ~ '^[+-]WT 003.*[BD]$'
             GROUP BY account_move_line__move_id.id, tag_name, tag.id, payment.id, commercial_partner.id
            )
            SELECT commercial_partner_name,
                   commercial_partner_vat,
                   fiscal_position_id,
                   date,
                   name,
                   jsonb_object_agg(tag_name, tag_amount) AS amounts_per_tags
            FROM tag_amounts_per_move
        GROUP BY commercial_partner_name, commercial_partner_vat, fiscal_position_id, date, name
        ORDER BY date desc, name desc
            """,
            table_references=query.from_clause,
            search_condition=query.where_clause,
            tag_name=self.env['account.account.tag'].with_context(lang='en_US')._field_to_sql('tag', 'name'),
        )
        self.env.cr.execute(query)
        fetched_row_data = self.env.cr.dictfetchall()

        fpos_ntax = ChartTemplate.ref('l10n_kh_fiscal_position_non_taxable_person', raise_if_not_found=False)
        fpos_oc = ChartTemplate.ref('l10n_kh_fiscal_position_overseas_company', raise_if_not_found=False)

        lines_data = []
        for index, row_data in enumerate(fetched_row_data, start=1):
            # Figure out the partner type based on their fpos
            if fpos_ntax and row_data['fiscal_position_id'] == fpos_ntax.id:
                partner_type = 2
            elif fpos_oc and row_data['fiscal_position_id'] == fpos_oc.id:
                partner_type = 3
            else:
                partner_type = 1

            amount_per_tag = row_data['amounts_per_tags']
            base_amount = sum(amount for tag, amount in amount_per_tag.items() if re.match(r'^WT 003.*B$', tag))

            lines_data.append([
                index,
                # Move Information
                format_date(self.env, row_data['date']),
                row_data['name'],
                # Partner Information
                partner_type,
                row_data['commercial_partner_vat'],
                row_data['commercial_partner_name'],
                _format_number(base_amount, currency),
                # Resident Tax Info
                _format_number(amount_per_tag.get('WT 003 R 01 D', 0.0), currency),
                _format_number(amount_per_tag.get('WT 003 R 02 D', 0.0), currency),
                _format_number(amount_per_tag.get('WT 003 R 03 D', 0.0), currency),
                _format_number(amount_per_tag.get('WT 003 R 04 D', 0.0), currency),
                _format_number(amount_per_tag.get('WT 003 R 05 D', 0.0), currency),
                _format_number(amount_per_tag.get('WT 003 R 06 D', 0.0), currency),
                # Non resident Tax Info
                _format_number(amount_per_tag.get('WT 003 NR 01 D', 0.0), currency),
                _format_number(amount_per_tag.get('WT 003 NR 02 D', 0.0), currency),
                _format_number(amount_per_tag.get('WT 003 NR 03 D', 0.0), currency),
                _format_number(amount_per_tag.get('WT 003 NR 04 D', 0.0), currency),
                _format_number(amount_per_tag.get('WT 003 NR 05 D', 0.0), currency),
            ])

        return lines_data

    def export_wt_003(self, options):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True, 'strings_to_formulas': False})

        report = self.env['account.report'].browse(options['report_id'])
        fonts = report._get_xlsx_export_fonts()

        sheet = workbook.add_worksheet('WT 003')

        # The two first lines (headers) are written in two languages, so we will increase their default height.
        # It won't fit perfectly (and we're not trying to, as some headers are quite big), but it should look better.
        sheet.set_row(0, 15 * 3)  # 15 being default
        sheet.set_row(1, 15 * 3)

        # Add headers
        self._write_headers(sheet, workbook, fonts)

        # Get the report data
        lines_data = self._get_wt_003_export_data(options)
        data_style = workbook.add_format({'font_name': 'Lato'})

        # Write the data.
        for i, line in enumerate(lines_data, start=2):
            for c, data in enumerate(line):  # Avoid using write_row to take full benefits of _set_xlsx_cell_sizes
                AccountReport._set_xlsx_cell_sizes(self, sheet, fonts, c, i, data, data_style, False)
                sheet.write(i, c, data)

        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()

        return {
            'file_name': 'wt_003.xlsx',
            'file_content': generated_file,
            'file_type': 'xlsx',
        }

    def _write_headers(self, sheet, workbook, fonts):
        """ Add the headers of the xlsx file.
        As with everything else in Cambodia, the report is expected to be written in both Khmer and English, and thus is
        not translated using gettext.
        """
        header_style = workbook.add_format({'font_name': 'Lato', 'align': 'center', 'valign': 'vcenter'})

        headers = {
            ('ល.រ', 'No.'): [],
            ('កាលបរិច្ឆេទ', 'Date'): [],
            ('លេខវិក្កយបត្រ', 'Invoice Number'): [],
            ('អ្នកទទួលប្រាក់', 'Recipient'): [
                ('ប្រភេទ', 'Type'),
                ('លេខសម្គាល់ការចុះបញ្ចីពន្ធដារ', 'TIN/BIN/TID'),
                ('ឈ្មោះ', 'Name'),
            ],
            ('ទឹកប្រាក់ត្រូវបើកមុនកាត់ទុក', 'Amount'): [],
            ('ពន្ធកាត់ទុកលើនិវាសជន', 'Withholding Tax on Residents'): [
                ('ការបំពេញសេវានានា សួយសារចំពោះទ្រព្យ អរូបីភាគកម្មក្នុងធនធានរ៉ែ', 'Performance of Service and \nRoyalty for intangibles, \ninterests in minerals(15%)'),
                ('ការបង់ការប្រាក់ឱ្យអ្នកជាប់ពន្ធ មិនមែនជាធនាគារ', 'Payment of interest to \nnon-bank or saving \ninstitution taxpayers(15%)'),
                ('ការបង់ការប្រាក់ឱ្យអ្នកជាប់ពន្ធ ដែលមានគណនីសន្សំមានកាលកំណត់', 'Payment of interest to \ntaxpayers who have fixed \nterm deposit accounts(6%)'),
                ('ការបង់ការប្រាក់ឱ្យអ្នកជាប់ពន្ធ ដែលមានគណនីសន្សំគ្មានកាលកំណត់', 'Payment of interest to \ntaxpayers who have \nnon-fixed term saving(4%)'),
                ('ការបង់ថ្លៃឈ្នួលចលនទ្រព្យ និង អចលនទ្រព្យ (នីតិបុគ្គល)', 'Payment of rental/lease of \nmovable and immovable \nproperty - Legal Person(10%)'),
                ('ការបង់ថ្លៃឈ្នួលចលនទ្រព្យ និង អចលនទ្រព្យ (រូបវន្តបុគ្គល)', 'Payment of rental/lease of \nmovable and immovable \nproperty - Physical Person(10%)'),
            ],
            ('ពន្ធកាត់ទុកលើនិវាសជន', 'Withholding Tax on Non-residents'): [
                ('ការបង់ការប្រាក់', 'Payment of Interest(14%)'),
                ('ការបង់សួយសារ ថ្លៃឈ្នួល ចំនូលផ្សេងៗទាក់ទិន និងការប្រើប្រាស់ទ្រព្យសម្បត្តិ', 'Payment of royalty, \nrental/leasing, and \nincome related to \nthe use of property(14%)'),
                ('ការទូទាត់ថ្លៃសេវាគ្រប់គ្រង និងសេវាបច្ចេកទេសនានា', 'Payment of management \nfee and technical \nservices(14%)'),
                ('ការបង់ភាគលាភ', 'Payment of Dividend(14%)'),
                ('សេវា', 'Service(14%)'),
            ],
        }

        col = 0
        for terms, sub_headers in headers.items():
            AccountReport._set_xlsx_cell_sizes(self, sheet, fonts, col, 0, '\n'.join(terms), header_style, True)
            if not sub_headers:
                sheet.merge_range(0, col, 1, col, '\n'.join(terms), header_style)
                col += 1
                continue

            offset = len(sub_headers) - 1
            sheet.merge_range(0, col, 0, col + offset, '\n'.join(terms), header_style)
            for x, sub_header_terms in enumerate(sub_headers):
                AccountReport._set_xlsx_cell_sizes(self, sheet, fonts, col + x, 1, '\n'.join(sub_header_terms), header_style, False)
                sheet.write(1, col + x, '\n'.join(sub_header_terms), header_style)
            col += offset + 1
