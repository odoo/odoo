# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError, RedirectWarning

import datetime
from lxml import etree

class DutchReportCustomHandler(models.AbstractModel):
    _inherit = 'l10n_nl.tax.report.handler'
    _description = 'Dutch Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options['buttons'].append({'name': _('XBRL'), 'sequence': 30, 'action': 'open_xbrl_wizard', 'file_export_type': _('XBRL')})

    def open_xbrl_wizard(self, options):
        statusinformatiservice_module = self.env['ir.module.module']._get('l10n_nl_reports_sbr_status_info')
        if statusinformatiservice_module.state != 'installed':
            raise RedirectWarning(
                message=_("A new module (l10n_nl_reports_sbr_status_info) needs to be installed for the service to track your submission status correctly."),
                action=self.env.ref('base.open_module_tree').id,
                button_text=_("Go to Apps"),
                additional_context={
                    'search_default_name': 'l10n_nl_reports_sbr_status_info',
                    'search_default_extra': True,
                },
            )
        report = self.env['account.report'].browse(options['report_id'])
        if report.filter_multi_company != 'tax_units' and len(options['companies']) > 1:
            raise UserError(_('Please select only one company to send the report. If you wish to aggregate multiple companies, please create a tax unit.'))
        date_to = datetime.date.fromisoformat(options['date']['date_to'])
        closing_date_from, closing_date_to = self.env.company._get_tax_closing_period_boundaries(date_to)
        new_options = report.get_options({
            **options,
            'date': {
                'date_from': closing_date_from,
                'date_to': closing_date_to,
                'mode': 'range',
                'filter': 'custom',
            },
            'integer_rounding_enabled': True,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tax Report SBR'),
            'view_mode': 'form',
            'res_model': 'l10n_nl_reports_sbr.tax.report.wizard',
            'target': 'new',
            'context': {
                'options': new_options,
                'default_date_from': closing_date_from,
                'default_date_to': closing_date_to,
                },
            'views': [[False, 'form']],
        }

    def export_tax_report_to_xbrl(self, options):
        # This will generate the XBRL file (similar style to XML).
        report = self.env['account.report'].browse(options['report_id'])
        lines = report._get_lines(options)
        data = self._generate_codes_values(lines, options.get('codes_values'))

        xbrl = self.env['ir.qweb']._render('l10n_nl_reports_sbr.tax_report_sbr', data)
        xbrl_element = etree.fromstring(xbrl)
        xbrl_file = etree.tostring(xbrl_element, xml_declaration=True, encoding='utf-8')
        return {
            'file_name': report.get_default_report_filename(options, 'xbrl'),
            'file_content': xbrl_file,
            'file_type': 'xml',
        }

    def _generate_codes_values(self, lines, codes_values=None):
        codes_values = codes_values or {}
        # Maps the needed taxes to their codewords used by the XBRL template.
        tax_report_lines_to_codes = {
            'l10n_nl.tax_report_rub_3c': 'InstallationDistanceSalesWithinTheEC',
            'l10n_nl.tax_report_rub_1e': 'SuppliesServicesNotTaxed',
            'l10n_nl.tax_report_rub_3a': 'SuppliesToCountriesOutsideTheEC',
            'l10n_nl.tax_report_rub_3b': 'SuppliesToCountriesWithinTheEC',
            'l10n_nl.tax_report_rub_1d': 'TaxedTurnoverPrivateUse',
            'l10n_nl.tax_report_rub_1a': 'TaxedTurnoverSuppliesServicesGeneralTariff',
            'l10n_nl.tax_report_rub_1c': 'TaxedTurnoverSuppliesServicesOtherRates',
            'l10n_nl.tax_report_rub_1b': 'TaxedTurnoverSuppliesServicesReducedTariff',
            'l10n_nl.tax_report_rub_4a': 'TurnoverFromTaxedSuppliesFromCountriesOutsideTheEC',
            'l10n_nl.tax_report_rub_4b': 'TurnoverFromTaxedSuppliesFromCountriesWithinTheEC',
            'l10n_nl.tax_report_rub_2a': 'TurnoverSuppliesServicesByWhichVATTaxationIsTransferred',
            'l10n_nl.tax_report_rub_btw_5b': 'ValueAddedTaxOnInput',
            'l10n_nl.tax_report_rub_btw_4a': 'ValueAddedTaxOnSuppliesFromCountriesOutsideTheEC',
            'l10n_nl.tax_report_rub_btw_4b': 'ValueAddedTaxOnSuppliesFromCountriesWithinTheEC',
            'l10n_nl.tax_report_rub_btw_5a': 'ValueAddedTaxOwed',
            'l10n_nl.tax_report_rub_btw_5g': 'ValueAddedTaxOwedToBePaidBack',
            'l10n_nl.tax_report_rub_btw_1d': 'ValueAddedTaxPrivateUse',
            'l10n_nl.tax_report_rub_btw_2a': 'ValueAddedTaxSuppliesServicesByWhichVATTaxationIsTransferred',
            'l10n_nl.tax_report_rub_btw_1a': 'ValueAddedTaxSuppliesServicesGeneralTariff',
            'l10n_nl.tax_report_rub_btw_1c': 'ValueAddedTaxSuppliesServicesOtherRates',
            'l10n_nl.tax_report_rub_btw_1b': 'ValueAddedTaxSuppliesServicesReducedTariff',
        }
        model_trl_to_codes = {}
        for tax_report_line_id, code in tax_report_lines_to_codes.items():
            model_trl_to_codes[self.env.ref(tax_report_line_id).id] = code

        for line in lines:
            code = model_trl_to_codes.get(self.env['account.report']._get_model_info_from_id(line['id'])[1])
            if code:
                codes_values[code] = str(int(line['columns'][0]['no_format']))
        return codes_values
