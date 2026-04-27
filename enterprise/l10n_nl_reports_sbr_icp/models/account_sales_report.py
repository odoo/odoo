from odoo import fields, models, _
from odoo.exceptions import RedirectWarning
from odoo.tools import cleanup_xml_node

from lxml import etree
import re

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

        date_to = fields.Date.to_date(options['date']['date_to'])
        template_xmlid = 'l10n_nl_reports_sbr_icp.icp_report_sbr'
        if date_to.year == 2024:
            # We still need to support the NT18 taxonomy for 2024 until that declaration period is over.
            template_xmlid = 'l10n_nl_reports_sbr_icp.icp_report_sbr_nt18'
        elif date_to.year == 2025:
            # We still need to support the NT19 taxonomy for 2025 until that declaration period is over.
            template_xmlid = 'l10n_nl_reports_sbr_icp.icp_report_sbr_nt19'

        report_template = self.env.ref(template_xmlid, raise_if_not_found=False)
        if not report_template:
            raise RedirectWarning(
                message=_(
                    "We couldn't find the correct export template for the year %(year)s. Please upgrade your module 'Netherlands - SBR ICP' and try again.",
                    year=date_to.year,
                ),
                action=self.env.ref('base.open_module_tree').id,
                button_text=_("Go to Apps"),
                additional_context={
                    'search_default_name': 'l10n_nl_reports_sbr_icp',
                    'search_default_extra': True,
                },
            )

        xbrl = self.env['ir.qweb']._render(report_template.id, data)
        xbrl_element = etree.fromstring(xbrl)
        xbrl_file = etree.tostring(cleanup_xml_node(xbrl_element, remove_blank_nodes=False), xml_declaration=True, encoding='utf-8')
        return {
            'file_name': report.get_default_report_filename(options, 'xbrl'),
            'file_content': xbrl_file,
            'file_type': 'xml',
        }

    def _generate_codes_values(self, report, lines, options):

        def get_country_and_vat(line, colname_to_idx):
            country = line['columns'][colname_to_idx['country_code']].get('name')
            vat = line['columns'][colname_to_idx['vat']].get('name')

            country = (country or '').strip().upper()
            vat = (vat or '').strip().upper()
            vat = re.sub(r'[^A-Z0-9]', '', vat)

            return country, vat

        def update_icp_context(contexts_map, country, vat):
            key = (country, vat)
            if key in contexts_map:
                return contexts_map[key]['contextRef']

            ctx_id = f"ICP_{country}_{vat or 'NOVAT'}"

            contexts_map[key] = {
                'contextRef': ctx_id,
                'country': country,
                'VATIdentificationNumberNational': vat,
            }
            return ctx_id

        codes_values = options.get('codes_values', {})
        codes_values.update({
            'IntraCommunitySupplies': [],
            'IntraCommunityServices': [],
            'IntraCommunityABCSupplies': [],
            'VATIdentificationNumberNLFiscalEntityDivision': self.env.company.vat[2:] if self.env.company.vat.startswith('NL') else self.env.company.vat,
        })

        icp_contexts_map = {}

        colname_to_idx = {col['expression_label']: idx for idx, col in enumerate(options.get('columns', []))}
        company_currency = self.env.company.currency_id

        for line in lines:
            if not line['columns'][colname_to_idx['vat']].get('no_format', 0):
                continue

            country, vat = get_country_and_vat(line, colname_to_idx)

            amount_product = line['columns'][colname_to_idx['amount_product']].get('no_format', 0)
            if company_currency.compare_amounts(amount_product, 0):
                ctx_id = update_icp_context(icp_contexts_map, country, vat)
                codes_values['IntraCommunitySupplies'].append({
                    'CountryCodeISO': country,
                    'SuppliesAmount': str(int(amount_product)),
                    'VATIdentificationNumberNational': vat,
                    'contextRef': ctx_id,
                })

            amount_service = line['columns'][colname_to_idx['amount_service']].get('no_format', 0)
            if company_currency.compare_amounts(amount_service, 0):
                ctx_id = update_icp_context(icp_contexts_map, country, vat)
                codes_values['IntraCommunityServices'].append({
                    'CountryCodeISO': country,
                    'ServicesAmount': str(int(amount_service)),
                    'VATIdentificationNumberNational': vat,
                    'contextRef': ctx_id,
                })

            amount_triangular = line['columns'][colname_to_idx['amount_triangular']].get('no_format', 0)
            if company_currency.compare_amounts(amount_triangular, 0):
                ctx_id = update_icp_context(icp_contexts_map, country, vat)
                codes_values['IntraCommunityABCSupplies'].append({
                    'CountryCodeISO': country,
                    'SuppliesAmount': str(int(amount_triangular)),
                    'VATIdentificationNumberNational': vat,
                    'contextRef': ctx_id,
                })

        codes_values['contexts'] = list(icp_contexts_map.values())

        return codes_values
