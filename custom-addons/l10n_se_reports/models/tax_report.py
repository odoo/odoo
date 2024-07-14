from odoo import models, _
from odoo.tools import float_repr
from lxml import etree
from lxml.objectify import fromstring


DOCTYPE = '<!DOCTYPE eSKDUpload PUBLIC "-//Skatteverket, Sweden//DTD Skatteverket eSKDUpload-DTD Version 6.0//SV" "https://www1.skatteverket.se/demoeskd/eSKDUpload_6p0.dtd">'


class SwedishTaxReportCustomHandler(models.AbstractModel):
    _name = 'l10n_se.tax.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'Swedish Tax Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options['buttons'].append({
            'name': _('XML'),
            'sequence': 30,
            'action': 'export_file',
            'action_param': 'l10n_se_export_tax_report_to_xml',
            'file_export_type': _('XML'),
        })

    def l10n_se_export_tax_report_to_xml(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        report_lines = report._get_lines(options)
        export_template = 'l10n_se_reports.tax_export_xml'
        colname_to_idx = {col['expression_label']: idx for idx, col in enumerate(options.get('columns', []))}
        lines_mapping = {
            line['columns'][colname_to_idx['balance']]['report_line_id']: float_repr(line['columns'][colname_to_idx['balance']]['no_format'], 0) for line in report_lines
        }
        template_context = {}
        for record in self.env['account.report.line'].browse(lines_mapping.keys()):
            template_context[record.code] = lines_mapping[record.id]
        template_context['org_number'] = report._get_sender_company_for_export(options).org_number
        template_context['period'] = (options['date']['date_to'][:4] + options['date']['date_to'][5:7])
        template_context['comment'] = ''

        qweb = self.env['ir.qweb']
        doc = qweb._render(export_template, values=template_context)
        tree = fromstring(doc)

        return {
            'file_name': report.get_default_report_filename(options, 'xml'),
            'file_content': etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding='ISO-8859-1', doctype=DOCTYPE),
            'file_type': 'xml',
        }
