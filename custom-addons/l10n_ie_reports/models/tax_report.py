# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
import stdnum.ie.pps
from datetime import timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, models, fields, _
from odoo.tools import float_repr, float_round
from odoo.exceptions import UserError


class IeTaxReportCustomHandler(models.AbstractModel):
    _name = 'l10n_ie.tax.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'Custom Tax Report Handler for Ireland'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options)
        if self.env.company.account_fiscal_country_id.code == 'IE':
            options.setdefault('buttons', []).append({
                'name': _('VAT3'),
                'sequence': 70,
                'action': 'export_file',
                'action_param': 'l10n_ie_export_vat3_to_xml',
                'file_export_type': _('XML')
            })

    @api.model
    def l10n_ie_export_vat3_to_xml(self, options):
        ''' Generate the VAT3 return in XML format. '''
        report = self.env['account.report'].browse(options['report_id'])
        values = self._l10n_ie_prepare_vat3_values(report, options)

        content = self.env['ir.qweb']._render('l10n_ie_reports.vat3_template', values)

        return {
            'file_name': report.get_default_report_filename(options, 'xml'),
            'file_content': '\n'.join(re.split(r'\n\s*\n', content)).encode(),
            'file_type': 'xml',
        }

    def _l10n_ie_prepare_vat3_values(self, report, options):
        ''' Generate the values for rendering the VAT3 return template. '''
        values = {
            'company': self.env.company,
            'float_repr': float_repr,
        }

        # Check company PPSN
        vat_country, vat_number = self.env['res.partner']._split_vat(self.env.company.vat)
        ppsn = self.env.company.company_registry or (vat_number if vat_country == 'ie' else self.env.company.vat)
        if not stdnum.ie.pps.is_valid(ppsn):
            raise UserError(_('You must set a valid PPSN number in the `Company Registry` field of your Company configuration.'))
        values['ppsn'] = ppsn

        # Compute filing frequency
        date_from = fields.Date.to_date(options['date']['date_from'])
        date_to = fields.Date.to_date(options['date']['date_to'])
        date_after = date_to + timedelta(days=1)
        delta = relativedelta(date_after, date_from)
        if delta == relativedelta(months=2):
            values['filefreq'] = '0'  # Bi-monthly
        elif delta == relativedelta(months=4):
            values['filefreq'] = '2'  # 4-monthly
        elif delta == relativedelta(months=6):
            values['filefreq'] = '3'  # 6-monthly
        else:
            values['filefreq'] = '1'  # Other

        values.update({
            'startdate': date_from.strftime('%d/%m/%Y'),
            'enddate': date_to.strftime('%d/%m/%Y'),
        })

        # Compute amount of sales, purchases, intra-EU goods and services, and postponed accounting imports
        lines = report._get_lines(options)
        lines_by_generic_id = {line['id']: line for line in lines}
        report_lines_to_extract = {
            'sale_vat': 'l10n_ie.l10n_ie_tr_T1',
            'purchase_vat': 'l10n_ie.l10n_ie_tr_T2',
            'eu_goods_sold': 'l10n_ie.l10n_ie_tr_E1',
            'eu_goods_bought': 'l10n_ie.l10n_ie_tr_E2',
            'eu_services_sold': 'l10n_ie.l10n_ie_tr_ES1',
            'eu_services_bought': 'l10n_ie.l10n_ie_tr_ES2',
            'postponed_accounting': 'l10n_ie.l10n_ie_tr_PA1',
        }
        for key, report_line_ref in report_lines_to_extract.items():
            generic_id = report._get_generic_line_id('account.report.line', self.env.ref(report_line_ref).id)
            line = lines_by_generic_id[generic_id]
            balance = line['columns'][-1]['no_format']  # We take the last column in case there is a comparison
            balance_whole = float_round(balance, precision_digits=0)  # Amounts should be in whole Euro
            values[key] = balance_whole

        return values
