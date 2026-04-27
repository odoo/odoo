import copy
import io
import zipfile

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import _, models, fields, api
from odoo.exceptions import UserError
from odoo.tools import SQL
from odoo.tools.misc import xlsxwriter


class IntrastatReportCustomHandler(models.AbstractModel):
    _inherit = 'account.intrastat.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        if self.env.company.account_fiscal_country_id.code != 'EE':
            return

        xml_button = {
            'name': _('XML'),
            'sequence': 30,
            'action': 'export_file',
            'action_param': 'ee_intrastat_export_to_xml',
            'file_export_type': _('XML'),
        }
        options['buttons'].append(xml_button)

        # Override the generic xlsx export to instead export official xlsx documents
        xlsx_button_option = next(button_opt for button_opt in options['buttons'] if button_opt.get('action_param') == 'export_to_xlsx')
        xlsx_button_option['action_param'] = 'ee_intrastat_export_to_xlsx'

    def _get_exporting_query_data(self):
        res = super()._get_exporting_query_data()
        return SQL('%s %s', res, SQL("""
            prodt.description AS goods_description,
            account_move_line.quantity AS quantity,
        """))

    def _get_exporting_dict_data(self, result_dict, query_res):
        super()._get_exporting_dict_data(result_dict, query_res)
        if self.env.company.account_fiscal_country_id.code == 'EE':
            result_dict.update({
                'goods_description': query_res['goods_description'],
                'system': result_dict['system'][0:2],
                'quantity': query_res['quantity'],
                'supplementary_units_code': query_res['supplementary_units_code'],
            })
        return result_dict

    def ee_intrastat_export_to_xlsx(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        include_arrivals, include_dispatches = super()._determine_inclusion(options)

        xlsx_files = []
        if include_arrivals:
            options_arrivals = self._ee_prepare_options_for_xlsx_export(options, 'arrivals')
            xlsx_files.append((
                _("arrivals_%s", report.get_default_report_filename(options, 'xlsx')),
                self._ee_generate_xlsx_report(options_arrivals),
            ))
        if include_dispatches:
            options_dispatches = self._ee_prepare_options_for_xlsx_export(options, 'dispatches')
            xlsx_files.append((
                _("dispatches_%s", report.get_default_report_filename(options, 'xlsx')),
                self._ee_generate_xlsx_report(options_dispatches),
            ))
        # Should never happen, just to make sure returned values below are valid
        if not xlsx_files:
            raise UserError(_("Something went wrong when generating xlsx file, please make sure to include arrivals, or dispatches, or both"))
        elif len(xlsx_files) == 1:
            return {
                'file_name': xlsx_files[0][0],
                'file_content': xlsx_files[0][1],
                'file_type': 'xlsx',
            }
        return self._ee_build_zip_response(report, options, xlsx_files)

    @api.model
    def _ee_prepare_options_for_xlsx_export(self, options, intrastat_type):
        """ Return a modified copy of the options, needed for the xlsx export to follow the
        correct grouping.
        """
        assert intrastat_type in {'arrivals', 'dispatches'}

        options_copy = copy.deepcopy(options)  # Necessary in case we reorder/filter the columns for both arrivals and dispatches

        options_copy['intrastat_grouped'] = False  # deactivate the grouping in case it's activated
        options_copy['intrastat_type'] = intrastat_type

        Move = self.env['account.move']
        move_types = Move.get_outbound_types(False) if intrastat_type == 'arrivals' else Move.get_inbound_types(False)
        options_copy.setdefault('forced_domain', []).append(('move_id.move_type', 'in', move_types))

        return options_copy

    @api.model
    def _ee_intrastat_xlsx_get_data(self, options):
        options['export_mode'] = 'file'
        report = self.env['account.report'].browse(options['report_id'])
        report._init_currency_table(options)
        expressions = report.line_ids.expression_ids
        report_results = self._report_custom_engine_intrastat(expressions, options, expressions[0].date_scope, 'id', None)
        for index, line_result in enumerate(report_results):
            report_results[index] = line_result[1]
        report_results = self._ee_prepare_values_for_export(report_results)

        col_orders_map = self._ee_get_col_order_and_title(options.get('intrastat_type'))

        results = []
        column_titles = list(col_orders_map.values())

        results.append(column_titles)

        # Add line rows
        for line in report_results:
            res_line = []
            for expression_label in col_orders_map:
                if expression_label == 'registry_code':
                    res_line.append(self.env.company.company_registry or '')
                elif expression_label == 'system':
                    res_line.append('1203' if line['system'] == '19' else '1204')
                elif expression_label == 'period':
                    res_line.append(fields.Date.from_string(options['date']['date_from']).strftime('%Y-%m'))
                else:
                    res_line.append(str(line.get(expression_label, '') or ''))

            results.append(res_line)

        return results

    @api.model
    def _ee_get_col_order_and_title(self, intrastat_type):
        """ Returns a dict of columns that should be present in the official xlsx file.
        The provided order must be respected. Each value in the dict corresponds to the
        expression_label of the column, and the keys represent the name of the column.
        """
        assert intrastat_type in {'arrivals', 'dispatches'}
        return {
            'arrivals': {
                'registry_code': _("Code of economic entity"),
                'system': _("Questionnaire code"),
                'period': _("Periodicity"),
                'country_code': _("EU Member State"),
                'transaction_code': _("Transaction"),
                'intrastat_product_origin_country_code': _("Country of Origin"),
                'commodity_code': _("CN8 goods code"),
                'weight': _("Net mass (kg)"),
                'supplementary_units': _("Supplementary quantity"),
                'supplementary_units_code': _("Unit"),
                'value': _("Value of goods in euros"),
                'goods_description': _("Description of goods"),
                'remark': _("Remark"),
            },
            'dispatches': {
                'registry_code': _("Code of economic entity"),
                'system': _("Questionnaire code"),
                'period': _("Periodicity"),
                'country_code': _("EU Member State"),
                'partner_vat': _("VAT number of the purchaser of the commodity in another Member State"),
                'transaction_code': _("Transaction"),
                'intrastat_product_origin_country_code': _("Country of Origin"),
                'commodity_code': _("CN8 goods code"),
                'weight': _("Net mass (kg)"),
                'supplementary_units': _("Supplementary quantity"),
                'supplementary_units_code': _("Unit"),
                'value': _("Value of goods in euros"),
                'goods_description': _("Description of goods"),
                'remark': _("Remark"),
            }
        }[intrastat_type]

    @api.model
    def _ee_generate_xlsx_report(self, options):
        with io.BytesIO() as output:
            with xlsxwriter.Workbook(output, {
                'in_memory': True,
                'strings_to_formulas': False,
            }) as workbook:
                self._ee_inject_report_into_xlsx_sheet(options, workbook, workbook.add_worksheet())

            return output.getvalue()

    @api.model
    def _ee_inject_report_into_xlsx_sheet(self, options, workbook, sheet):
        title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
        line_style = workbook.add_format({'font_name': 'Arial', 'font_size': 11, 'font_color': '#666666'})

        sheet.set_column(0, len(options['columns']), 25)  # set a length of 25 for each column

        results = self._ee_intrastat_xlsx_get_data(options)
        for line_offset, line in enumerate(results):
            for col_offset, value in enumerate(line):
                sheet.write(line_offset, col_offset, value, title_style if line_offset == 0 else line_style)

    def ee_intrastat_export_to_xml(self, options):
        options['export_mode'] = 'file'
        report = self.env['account.report'].browse(options['report_id'])
        date_from = fields.Date.to_date(options['date']['date_from'])
        date_to = fields.Date.to_date(options['date']['date_to'])
        final_day_month = date_from + relativedelta(day=31)
        if date_from.day != 1 or date_to != final_day_month:
            raise UserError(_('Wrong date range selected. The intrastat declaration export has to be done monthly.'))

        report._init_currency_table(options)
        expressions = report.line_ids.expression_ids
        results = self._report_custom_engine_intrastat(expressions, options, expressions[0].date_scope, 'id', None)
        for index, line_result in enumerate(results):
            results[index] = line_result[1]
        results = self._ee_prepare_values_for_export(results)

        today = datetime.today()

        in_vals = [elem for elem in results if elem['intrastat_type'] == 'Arrival']
        out_vals = [elem for elem in results if elem['intrastat_type'] == 'Dispatch']

        file_content = self.env['ir.qweb']._render('l10n_ee_intrastat.intrastat_report_export_xml', {
            'company': self.env.company,
            'envelopeId': f"SE{today.strftime('%Y%m%d%H%M%S')}",
            'user': self.env.user,
            'in_vals': in_vals,
            'out_vals': out_vals,
            'in_vals_total_weight': round(sum(float(elem['weight']) for elem in in_vals), 3),
            'out_vals_total_weight': round(sum(float(elem['weight']) for elem in out_vals), 3),
            'in_vals_total_amount': round(sum(elem['value'] for elem in in_vals), 3),
            'out_vals_total_amount': round(sum(elem['value'] for elem in out_vals), 3),
            'date': date_from.strftime('%Y-%m'),
            'sending_date': today,
            'is_test': False,
            'version': f'Odoo {self.sudo().env.ref("base.module_base").latest_version}',
            'number_of_declarations': bool(in_vals) + bool(out_vals),
        })

        return {
            'file_name': self.env['account.report'].browse(options['report_id']).get_default_report_filename(options, 'xml'),
            'file_content': file_content,
            'file_type': 'xml',
        }

    def _ee_get_query_res(self, options):
        query, params = self._prepare_query(options)
        self._cr.execute(query, params)
        query_res = self._cr.dictfetchall()
        query_res = self._fill_missing_values(query_res)
        query_res = self._ee_prepare_values_for_export(query_res)
        return query_res

    @api.model
    def _ee_prepare_values_for_export(self, vals_list):
        for count, vals in enumerate(sorted(vals_list, key=lambda x: x['intrastat_type']), start=1):
            vals['value'] = round(vals['value'], 3)
            vals['itemNumber'] = count
            vals['quantity'] = round(vals['quantity'] * float(vals['supplementary_units']) if vals['supplementary_units'] else vals['quantity'], 2)
            vals['weight'] = float(vals['weight']) if vals['weight'] else 0
        return vals_list

    @api.model
    def _ee_build_zip_response(self, report, options, xlsx_files):
        with io.BytesIO() as buffer:
            with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as zipfile_obj:
                for filename, file_content in xlsx_files:
                    zipfile_obj.writestr(filename, file_content)

            return {
                'file_name': report.get_default_report_filename(options, 'zip'),
                'file_content': buffer.getvalue(),
                'file_type': 'zip',
            }
