# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import RedirectWarning

from lxml import etree

class DutchECSalesReportCustomHandler(models.AbstractModel):
    _inherit = 'l10n_nl.ec.sales.report.handler'
    _description = 'Dutch EC Sales Report Custom Handler for SBR'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)
        options['buttons'].append({'name': _('XBRL'), 'sequence': 40, 'action': 'open_xbrl_wizard', 'file_export_type': _('XBRL')})

    def open_xbrl_wizard(self, options):
        omzetbelasting_module = self.env['ir.module.module']._get('l10n_nl_reports_sbr_status_info')
        if omzetbelasting_module.state != 'installed':
            raise RedirectWarning(
                message=_("A new module (l10n_nl_reports_sbr_status_info) needs to be installed for the service to work correctly."),
                action=self.env.ref('base.open_module_tree').id,
                button_text=_("Go to Apps"),
                additional_context={
                    'search_default_name': 'l10n_nl_reports_sbr_status_info',
                    'search_default_extra': True,
                },
            )
        res = self.env['l10n_nl.tax.report.handler'].open_xbrl_wizard(options)
        res.update({
            'name': _('EC Sales (ICP) SBR'),
            'res_model': 'l10n_nl_reports_sbr_icp.icp.wizard',
        })
        for ec_tax_filter in res['context']['options']['ec_tax_filter_selection']:
            ec_tax_filter['selected'] = True
        return res

    def export_icp_report_to_xbrl(self, options):
        # This will generate the XBRL file (similar style to XML).
        report = self.env['account.report'].browse(options['report_id'])
        lines = report._get_lines(options)
        data = self._generate_codes_values(report, lines, options)

        xbrl = self.env['ir.qweb']._render('l10n_nl_reports_sbr_icp.icp_report_sbr', data)
        xbrl_element = etree.fromstring(xbrl)
        xbrl_file = etree.tostring(xbrl_element, xml_declaration=True, encoding='utf-8')
        return {
            'file_name': report.get_default_report_filename(options, 'xbrl'),
            'file_content': xbrl_file,
            'file_type': 'xml',
        }

    def _generate_codes_values(self, report, lines, options):
        codes_values = options.get('codes_values', {})
        codes_values.update({
            'IntraCommunitySupplies': [],
            'IntraCommunityServices': [],
            'IntraCommunityABCSupplies': [],
            'VATIdentificationNumberNLFiscalEntityDivision': self.env.company.vat[2:] if self.env.company.vat.startswith('NL') else self.env.company.vat,
        })

        colname_to_idx = {col['expression_label']: idx for idx, col in enumerate(options.get('columns', []))}
        company_currency = self.env.company.currency_id
        for line in lines:
            if report._get_markup(line['id']) != 'total':
                if company_currency.compare_amounts(line['columns'][colname_to_idx['amount_product']].get('no_format', 0), 0) == 1:
                    codes_values['IntraCommunitySupplies'].append({
                        'CountryCodeISO': line['columns'][colname_to_idx['country_code']].get('name'),
                        'SuppliesAmount': str(int(line['columns'][colname_to_idx['amount_product']].get('no_format'))),
                        'VATIdentificationNumberNational': line['columns'][colname_to_idx['vat']].get('name'),
                    })
                if company_currency.compare_amounts(line['columns'][colname_to_idx['amount_service']].get('no_format', 0), 0) == 1:
                    codes_values['IntraCommunityServices'].append({
                        'CountryCodeISO': line['columns'][colname_to_idx['country_code']].get('name'),
                        'ServicesAmount': str(int(line['columns'][colname_to_idx['amount_service']].get('no_format'))),
                        'VATIdentificationNumberNational': line['columns'][colname_to_idx['vat']].get('name', 0),
                    })
                if company_currency.compare_amounts(line['columns'][colname_to_idx['amount_triangular']].get('no_format', 0), 0) == 1:
                    codes_values['IntraCommunityABCSupplies'].append({
                        'CountryCodeISO': line['columns'][colname_to_idx['country_code']].get('name'),
                        'SuppliesAmount': str(int(line['columns'][colname_to_idx['amount_triangular']].get('no_format'))),
                        'VATIdentificationNumberNational': line['columns'][colname_to_idx['vat']].get('name'),
                    })
        return codes_values
