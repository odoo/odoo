import io

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools.misc import xlsxwriter


class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        if self.env.company.partner_id.country_id.code != 'ES':
            return

        # Add the libro diario XLSX download button
        options['buttons'].append({
            'name': _('Libro Diario XLSX'),
            'sequence': 21,
            'action': 'export_file',
            'action_param': 'es_libro_diario_export_to_xlsx',
            'file_export_type': 'XLSX',
            'branch_allowed': True,
        })

    def es_libro_diario_export_to_xlsx(self, options):
        """ Exports a xlsx document containing the required libro diario data, compliant with the official format."""
        return self._es_libro_diario_generate_xlsx_report(options=options)

    @api.model
    def _es_libro_diario_generate_xlsx_report(self, options):
        with io.BytesIO() as output:
            with xlsxwriter.Workbook(output, {
                'in_memory': True,
                'strings_to_formulas': False,
            }) as workbook:
                self._es_libro_diario_inject_report_into_xlsx_sheet(options, workbook, workbook.add_worksheet())
            return  {
                'file_name': "libro_diario.xlsx",
                'file_content': output.getvalue(),
                'file_type': 'xlsx',
            }

    @api.model
    def _es_libro_diario_inject_report_into_xlsx_sheet(self, options, workbook, sheet):
        header_style = workbook.add_format({'font_name': 'Arial', 'bold': True})
        title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
        line_style = workbook.add_format({'font_name': 'Arial', 'font_size': 11})

        sheet.set_column(0, 0, 20)  # Company data + Entry
        sheet.set_column(1, 1, 10)  # Line
        sheet.set_column(2, 2, 15)  # Date
        sheet.set_column(3, 3, 70)  # Label
        sheet.set_column(4, 4, 25)  # Move Name
        sheet.set_column(5, 5, 15)  # Account code
        sheet.set_column(6, 6, 30)  # Account name
        sheet.set_column(7, 8, 13)  # Debit and Credit

        header, data = self._es_libro_diario_xlsx_get_data(options)
        padding = 2  # nb of lines between the header and AMLs data

        for line_offset, line in enumerate(header):
            for col_offset, value in enumerate(line):
                sheet.write(line_offset, col_offset, value, header_style)

        for line_offset, line in enumerate(data):
            style = title_style if line_offset == 0 else line_style
            for col_offset, value in enumerate(line):
                sheet.write(len(header) + padding + line_offset, col_offset, value, style)

    @api.model
    def _es_libro_diario_xlsx_get_data(self, options):
        company_ids = [company['id'] for company in options['companies']]
        companies = self.env['res.company'].browse(company_ids)
        if any(companies.filtered(lambda company: company.partner_id.country_id.code != 'ES')):
            raise UserError(_('This report export is only available for ES companies.'))

        report = self.env['account.report'].browse(options['report_id'])
        report._init_currency_table(options)
        aml_query = self._get_query_amls(report, options, None)

        custom_libro_diario_columns = {
            'entry': _("Entry"),
            'line':  _("Line"),
            'date': _("Date"),
            'name': _("Description"),
            'move_name': _("Document"),
            'account_code': _("Account Code"),
            'account_name': _("Account Name"),
            'debit': _("Debit"),
            'credit': _("Credit"),
        }

        # Add company data and report dates
        company = report._get_sender_company_for_export(options)
        company_data = [company.name, company.vat or ""]
        report_data = [_("General Ledger - %(date_from)s_%(date_to)s", date_from=options['date']['date_from'], date_to=options['date']['date_to'])]

        header = [company_data, report_data]

        # Add the column names
        data = [list(custom_libro_diario_columns.values())]

        # Add lines data
        current_move = ''
        entry_index = 0
        self._cr.execute(aml_query)
        for aml in self._cr.dictfetchall():
            if not current_move or current_move != aml['move_name']:
                current_move = aml['move_name']
                entry_index += 1
                line_index = 1
            else:
                line_index += 1

            res_line = []
            for column in custom_libro_diario_columns:
                if column == 'entry':
                    res_line.append(entry_index)
                elif column == 'line':
                    res_line.append(line_index)
                elif column == 'date':
                    res_line.append(aml['date'].strftime("%d/%m/%Y"))
                else:
                    res_line.append(aml[column])
            data.append(res_line)

        return header, data
