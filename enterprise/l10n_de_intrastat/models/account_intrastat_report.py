from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import _, models, fields, api
from odoo.exceptions import UserError
from odoo.tools import SQL


class IntrastatReportCustomHandler(models.AbstractModel):
    _inherit = 'account.intrastat.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        if self.env.company.partner_id.country_id.code != 'DE':
            return

        xml_button = {
            'name': _('XML'),
            'sequence': 30,
            'action': 'export_file',
            'action_param': 'de_intrastat_export_to_xml',
            'file_export_type': _('XML'),
        }
        options['buttons'].append(xml_button)

    def _get_exporting_query_data(self):
        res = super()._get_exporting_query_data()
        return SQL('%s %s', res, SQL("""
            prodt.description AS goods_description,
            account_move_line.quantity AS quantity,
        """))

    def _get_exporting_dict_data(self, result_dict, query_res):
        super()._get_exporting_dict_data(result_dict, query_res)
        if self.env.company.partner_id.country_id.code == 'DE':
            result_dict.update({
                'goods_description': query_res['goods_description'],
                'system': result_dict['system'][0:2],
                'quantity': query_res['quantity'],
                'supplementary_units_code': query_res['supplementary_units_code'],
            })
        return result_dict

    def de_intrastat_export_to_xml(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        date_from = fields.Date.to_date(options['date']['date_from'])
        date_to = fields.Date.to_date(options['date']['date_to'])
        final_day_month = date_from + relativedelta(day=31)
        if date_from.day != 1 or date_to != final_day_month:
            raise UserError(_('Wrong date range selected. The intrastat declaration export has to be done monthly.'))
        date = date_from.strftime('%Y-%m')

        in_vals = []
        out_vals = []

        report._init_currency_table(options)
        expressions = report.line_ids.expression_ids
        results = self._report_custom_engine_intrastat(expressions, options, expressions[0].date_scope, 'id', None)
        for index, line_result in enumerate(results):
            results[index] = line_result[1]
        results = self._prepare_values_for_de_export(results)

        for line in results:
            if line['system'] == '29':
                in_vals.append(line)
            else:
                out_vals.append(line)

        today = datetime.today()

        file_content = self.env['ir.qweb']._render('l10n_de_intrastat.intrastat_report_export_xml', {
            'company': self.env.company,
            'envelopeId': f"XGT-{date_from.strftime('%Y%m')}-{today.strftime('%Y%m%d')}-{today.strftime('%H%M')}",
            'user': self.env.user,
            'in_vals': in_vals,
            'out_vals': out_vals,
            'in_vals_total_weight': round(sum(float(elem['weight']) for elem in in_vals), 3),
            'out_vals_total_weight': round(sum(float(elem['weight']) for elem in out_vals), 3),
            'in_vals_total_amount': round(sum(elem['value'] for elem in in_vals), 3),
            'out_vals_total_amount': round(sum(elem['value'] for elem in out_vals), 3),
            'date': date,
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

    @api.model
    def _prepare_values_for_de_export(self, vals_list):
        for count, vals in enumerate(vals_list, start=1):
            vals['value'] = round(vals['value'], 3)
            vals['itemNumber'] = count
            vals['quantity'] = round(vals['quantity'] * float(vals['supplementary_units']) if vals['supplementary_units'] else vals['quantity'], 2)
        return vals_list
