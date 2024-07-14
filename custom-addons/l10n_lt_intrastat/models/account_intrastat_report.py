# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning


class IntrastatReportCustomHandler(models.AbstractModel):
    _inherit = 'account.intrastat.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        if self.env.company.partner_id.country_id.code != 'LT':
            return

        xml_button = {
            'name': _('XML'),
            'sequence': 30,
            'action': 'export_file',
            'action_param': 'lt_intrastat_export_to_xml',
            'file_export_type': _('XML'),
        }
        options['buttons'].append(xml_button)

    def _show_region_code(self):
        # The region code is irrelevant for the Lithuania and will always be an empty column, with
        # this function we can conditionally exclude it from the report.
        if self.env.company.account_fiscal_country_id.code == 'LT':
            return False
        return super()._show_region_code()

    @api.model
    def lt_intrastat_export_to_xml(self, options):
        # Generate XML content
        date_1 = fields.Date.to_date(options['date']['date_from'])
        date_2 = fields.Date.to_date(options['date']['date_to'])
        final_day_month = date_1 + relativedelta(day=31)
        if date_1.day != 1 or date_2 != final_day_month:
            raise UserError(_('Wrong date range selected. The intrastat declaration export has to be done monthly.'))
        date = date_1.strftime('%Y-%m')

        company = self.env.company
        user = self.env.user
        if not company.company_registry:
            error_msg = _('Missing company registry information on the company')
            action_error = {
                'name': _('company %s', company.name),
                'type': 'ir.actions.act_window',
                'res_model': 'res.company',
                'views': [[False, 'form']],
                'target': 'new',
                'res_id': company.id,
            }
            raise RedirectWarning(error_msg, action_error, _('Add company registry'))

        query, params = self._prepare_query(options)
        self._cr.execute(query, params)  # pylint: disable=sql-injection
        query_res = self._cr.dictfetchall()
        query_res = self._fill_missing_values(query_res)
        query_res = self._prepare_values_for_export(query_res)

        version = f'Odoo {self.sudo().env.ref("base.module_base").latest_version}'
        total_invoiced_amount = sum([item['value'] for item in query_res])

        today = datetime.today()
        envelopeId = f"VK{today.strftime('%Y%m%d%H%M%S')}"

        file_content = self.env['ir.qweb']._render('l10n_lt_intrastat.intrastat_report_export_xml', {
            'company': company,
            'envelopeId': envelopeId,
            'user': user,
            'in_vals': [elem for elem in query_res if elem['type'] == 'Arrival'],
            'out_vals': [elem for elem in query_res if elem['type'] == 'Dispatch'],
            'total_invoiced_amount': round(total_invoiced_amount),
            'extended': options.get('intrastat_extended'),
            'date': date,
            'sending_date': today,
            'is_test': False,
            'version': version,
            'number_of_declarations': len(query_res),
        })

        return {
            'file_name': self.env['account.report'].browse(options['report_id']).get_default_report_filename(options, 'xml'),
            'file_content': file_content,
            'file_type': 'xml',
        }

    @api.model
    def _prepare_values_for_export(self, vals_list):
        for count, vals in enumerate(vals_list, start=1):
            vals['weight'] = f'{round(vals["weight"]*1000):>06}'
            vals['value'] = round(vals['value'])
            vals['itemNumber'] = count
        return vals_list
