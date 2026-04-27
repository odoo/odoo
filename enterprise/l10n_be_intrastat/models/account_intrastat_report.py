# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning
from odoo.tools import SQL
from odoo.tools.float_utils import float_round

from lxml import etree


class IntrastatReportCustomHandler(models.AbstractModel):
    _inherit = 'account.intrastat.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        if self.env.company.account_fiscal_country_id.code != 'BE':
            return

        options['buttons'].extend([
            {
                'name': _('XML'),
                'sequence': 30,
                'action': 'export_file',
                'action_param': 'be_intrastat_export_to_xml',
                'file_export_type': _('XML'),
            },
            {
                'name': _('CSV'),
                'sequence': 40,
                'action': 'export_file',
                'action_param': 'be_intrastat_export_to_csv',
                'file_export_type': _('CSV'),
            },
        ])

    def _show_region_code(self):
        if self.env.company.account_fiscal_country_id.code == 'BE' and not self.env.company.intrastat_region_id:
            return False
        return super()._show_region_code()

    @api.model
    def _be_intrastat_get_report_results_for_file_export(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        options = report.get_options(previous_options={**options, 'export_mode': 'file'})
        self._check_date_range(options)
        report._init_currency_table(options)
        query_params = {'product_type_condition': SQL("AND (account_move_line.product_id IS NOT NULL AND prodt.type != 'service')")}
        query = self._get_intrastat_report_query(report, options, 'intrastat_grouping', query_params=query_params)
        self._cr.flush()
        self._cr.execute(query)
        return self._cr.dictfetchall()

    @api.model
    def be_intrastat_export_to_csv(self, options):
        results = self._be_intrastat_get_report_results_for_file_export(options)
        file_content = self._be_intrastat_get_csv_file_content(options, results)
        return {
            'file_name': self.env['account.report'].browse(options['report_id']).get_default_report_filename(options, 'csv'),
            'file_content': file_content,
            'file_type': 'csv',
        }

    @api.model
    def _be_intrastat_get_csv_file_content(self, options, results):
        file_content = ''
        base_columns = ['system', 'country_code', 'transaction_code', 'region_code', 'commodity_code',
                    'weight', 'supplementary_units', 'value']
        if options['intrastat_extended']:
            base_columns += ['transport_code', 'incoterm_code']
        system_29_columns = base_columns + ['intrastat_product_origin_country_code', 'partner_vat']
        for result in results:
            result['system'] = result['system'][:2]
            columns = system_29_columns if result['system'] == '29' else base_columns
            file_content += ';'.join([
                str(int(float_round(result.get(col) or 0, 0))) if col == 'value' else str(result.get(col) or '') for col in columns
            ]) + '\n'
        return file_content

    @api.model
    def be_intrastat_export_to_xml(self, options):
        results = self._be_intrastat_get_report_results_for_file_export(options)
        company = self.env.company
        if not company.company_registry:
            error_msg = _('Missing company registry information on the company')
            action_error = {
                'name': _('company %s', company.name),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'res.company',
                'views': [[False, 'form']],
                'target': 'new',
                'res_id': company.id,
            }
            raise RedirectWarning(error_msg, action_error, _('Add company registry'))
        file_content = self._be_intrastat_get_xml_file_content(options, results, company)
        return {
            'file_name': self.env['account.report'].browse(options['report_id']).get_default_report_filename(options, 'xml'),
            'file_content': etree.tostring(etree.fromstring(file_content), xml_declaration=True, encoding='utf-8', pretty_print=True),
            'file_type': 'xml',
        }

    @api.model
    def _be_intrastat_get_xml_file_content(self, options, results, company):
        in_vals = []
        out_vals = []
        for line in results:
            line['system'] = line['system'][0:2]
            if line['system'] == '19':
                in_vals.append(line)
            else:
                out_vals.append(line)

        return self.env['ir.qweb']._render('l10n_be_intrastat.intrastat_report_export_xml', {
            'company': company,
            'in_vals': in_vals,
            'out_vals': out_vals,
            'extended': options.get('intrastat_extended'),
            'date': fields.Date.to_date(options['date']['date_from']).strftime('%Y-%m'),
            'incl_arrivals': options['intrastat_type'][0]['selected'] or not options['intrastat_type'][1]['selected'],
            'incl_dispatches': options['intrastat_type'][1]['selected'] or not options['intrastat_type'][0]['selected'],
            '_get_reception_code': self._get_reception_code,
            '_get_reception_form': self._get_reception_form,
            '_get_expedition_code': self._get_expedition_code,
            '_get_expedition_form': self._get_expedition_form,
            'hide_0_lines': options.get('hide_0_lines'),
        })

    def _get_reception_code(self, extended):
        return 'EX19E' if extended else 'EX19S'

    def _get_reception_form(self, extended):
        return 'EXF19E' if extended else 'EXF19S'

    def _get_expedition_code(self, extended):
        return 'INTRASTAT_X_E' if extended else 'INTRASTAT_X_S'

    def _get_expedition_form(self, extended):
        return 'INTRASTAT_X_EF' if extended else 'INTRASTAT_X_SF'
