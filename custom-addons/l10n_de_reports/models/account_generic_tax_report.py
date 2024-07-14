from odoo import api, models, _
from odoo.exceptions import RedirectWarning
from odoo.tools import float_repr

from lxml import etree
from datetime import date, datetime


class GermanTaxReportCustomHandler(models.AbstractModel):
    _name = 'l10n_de.tax.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'German Tax Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options.setdefault('buttons', []).append(
            {
                'name': _('XML'),
                'sequence': 30,
                'action': 'export_file',
                'action_param': 'export_tax_report_to_xml',
                'file_export_type': _('XML'),
            }
        )

    @api.model
    def _redirect_to_misconfigured_company_number(self, message):
        """ Raises a RedirectWarning informing the user his company is missing configuration, redirecting him to the
         tree view of res.company
        """
        action = self.env.ref('base.action_res_company_form')

        raise RedirectWarning(
            message,
            action.id,
            _("Configure your company"),
        )

    def export_tax_report_to_xml(self, options):

        if self.env.company.l10n_de_stnr:
            steuer_nummer = self.env.company.get_l10n_de_stnr_national()
        else:
            self._redirect_to_misconfigured_company_number(_("Your company's SteuerNummer field should be filled"))

        report = self.env['account.report'].browse(options['report_id'])
        template_context = {}
        options = report.get_options(options)
        date_to = datetime.strptime(options['date']['date_to'], '%Y-%m-%d')
        template_context['year'] = date_to.year
        if options['date']['period_type'] == 'month':
            template_context['period'] = date_to.strftime("%m")
        elif options['date']['period_type'] == 'quarter':
            month_end = int(date_to.month)
            if month_end % 3 != 0:
                raise ValueError('Quarter not supported')
            # For quarters, the period should be 41, 42, 43, 44 depending on the quarter.
            template_context['period'] = int(month_end / 3 + 40)
        template_context['creation_date'] = date.today().strftime("%Y%m%d")
        template_context['company'] = report._get_sender_company_for_export(options)

        qweb = self.env['ir.qweb']
        doc = qweb._render('l10n_de_reports.tax_export_xml', values=template_context)
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.fromstring(doc, parser)

        taxes = tree.xpath('//Umsatzsteuervoranmeldung')[0]
        tax_number = tree.xpath('//Umsatzsteuervoranmeldung/Steuernummer')[0]
        tax_number.text = steuer_nummer

        # Add the values dynamically. We do it here because the tag is generated from the code and
        # Qweb doesn't allow dynamically generated tags.

        report_lines = report._get_lines(options)
        colname_to_idx = {col['expression_label']: idx for idx, col in enumerate(options.get('columns', []))}
        report_line_ids = [line['columns'][colname_to_idx['balance']]['report_line_id'] for line in report_lines]
        codes_context = {}
        for record in self.env['account.report.line'].browse(report_line_ids):
            codes_context[record.id] = record.code

        for line in report_lines:
            line_code = codes_context[line['columns'][colname_to_idx['balance']]['report_line_id']]
            if not (line_code and line_code.startswith('DE') and not line_code.endswith('TAX')):
                continue
            line_code = line_code.split('_')[1]
            # all "Kz" may be supplied as negative, except "Kz37", "Kz39", "Kz50"
            line_value = line['columns'][colname_to_idx['balance']]['no_format']
            if line_value and (line_code not in ("37", "39", "50") or line_value > 0):
                elem = etree.SubElement(taxes, "Kz" + line_code)
                # These can not be supplied with decimals
                if line_code in ("21", "35", "41", "42", "43", "44", "45", "46", "48", "49", "50", "60", "73",
                                 "76", "77", "81", "84", "86", "87", "89", "91", "93", "90", "94", "95"):
                    elem.text = float_repr(int(line_value), 0)
                elif line_code in ("66", "61", "62", "67", "63", "59", "64",):
                    # These are taxes that are on the wrong sign on the report compared to what should be exported
                    elem.text = float_repr(- line_value, 2).replace('.', ',')
                else:
                    elem.text = float_repr(line_value, 2).replace('.', ',')

            # "kz83" must be supplied with 0.00 if it doesn't have balance
            elif line_code == "83":
                elem = etree.SubElement(taxes, "Kz" + line_code)
                elem.text = "0,00"

        return {
            'file_name': report.get_default_report_filename(options, 'xml'),
            'file_content': etree.tostring(tree, pretty_print=True, standalone=False, encoding='ISO-8859-1',),
            'file_type': 'xml',
        }
