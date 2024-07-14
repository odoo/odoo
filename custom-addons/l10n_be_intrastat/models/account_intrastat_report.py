# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError, RedirectWarning
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

from datetime import datetime, timedelta
from lxml import etree


class IntrastatReportCustomHandler(models.AbstractModel):
    _inherit = 'account.intrastat.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        if self.env.company.partner_id.country_id.code != 'BE':
            return

        xml_button = {
            'name': _('XML'),
            'sequence': 30,
            'action': 'export_file',
            'action_param': 'be_intrastat_export_to_xml',
            'file_export_type': _('XML'),
        }
        options['buttons'].append(xml_button)
        options['intrastat_grouped'] = previous_options.get('intrastat_grouped', True)

    def _show_region_code(self):
        if self.env.company.account_fiscal_country_id.code == 'BE' and not self.env.company.intrastat_region_id:
            return False
        return super()._show_region_code()

    @api.model
    def be_intrastat_export_to_xml(self, options):
        # Generate XML content
        date_1 = datetime.strptime(options['date']['date_from'], DEFAULT_SERVER_DATE_FORMAT)
        date_2 = datetime.strptime(options['date']['date_to'], DEFAULT_SERVER_DATE_FORMAT)
        a_day = timedelta(days=1)
        if date_1.day != 1 or (date_2 - date_1) > timedelta(days=30) or date_1.month == (date_2 + a_day).month:
            raise UserError(_('Wrong date range selected. The intrastat declaration export has to be done monthly.'))
        date = date_1.strftime('%Y-%m')

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

        self.env.cr.flush()
        query, params = self._build_query_group(options)
        self._cr.execute(query, params)  # pylint: disable=sql-injection
        query_res = self._cr.dictfetchall()
        query_res = self._fill_missing_values(query_res)

        # create in_vals (resp. out_vals) corresponding to invoices with cash-in (resp. cash-out)
        in_vals = []
        out_vals = []
        for result in query_res:
            in_vals.append(result) if result['type'] == 'Arrival' else out_vals.append(result)

        file_content = self.env['ir.qweb']._render('l10n_be_intrastat.intrastat_report_export_xml', {
            'company': company,
            'in_vals': in_vals,
            'out_vals': out_vals,
            'extended': options.get('intrastat_extended'),
            'date': date,
            'incl_arrivals': options['intrastat_type'][0]['selected'] or not options['intrastat_type'][1]['selected'],
            'incl_dispatches': options['intrastat_type'][1]['selected'] or not options['intrastat_type'][0]['selected'],
            '_get_reception_code': self._get_reception_code,
            '_get_reception_form': self._get_reception_form,
            '_get_expedition_code': self._get_expedition_code,
            '_get_expedition_form': self._get_expedition_form,
        })

        return {
            'file_name': self.env['account.report'].browse(options['report_id']).get_default_report_filename(options, 'xml'),
            'file_content': etree.tostring(etree.fromstring(file_content), xml_declaration=True, encoding='utf-8', pretty_print=True),
            'file_type': 'xml',
        }

    def _get_reception_code(self, extended):
        return 'EX19E' if extended else 'EX19S'

    def _get_reception_form(self, extended):
        return 'EXF19E' if extended else 'EXF19S'

    def _get_expedition_code(self, extended):
        return 'INTRASTAT_X_E' if extended else 'INTRASTAT_X_S'

    def _get_expedition_form(self, extended):
        return 'INTRASTAT_X_EF' if extended else 'INTRASTAT_X_SF'
