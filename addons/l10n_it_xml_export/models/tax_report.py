from dateutil.relativedelta import relativedelta
from lxml import etree
from markupsafe import Markup

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import file_open, xml_utils

class ItalianReportCustomHandler(models.AbstractModel):
    _name = 'l10n_it.monthly.tax.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'Italian Monthly Tax Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        options.setdefault("buttons", []).append({
            "name": _("XML"),
            "sequence": 30,
            "action": "print_tax_report_to_xml",
            "file_export_type": _("XML"),
            "branch_allowed": True,
        })

    def print_tax_report_to_xml(self, options):
        view_id = self.env.ref('l10n_it_xml_export.monthly_tax_report_xml_export_wizard_view').id
        return {
            'name': _('XML Export Options'),
            'view_mode': 'form',
            'views': [[view_id, 'form']],
            'res_model': 'l10n_it_xml_export.monthly.tax.report.xml.export.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': dict(self._context, l10n_it_xml_export_monthly_tax_report_options=options),
        }

    def export_tax_report_to_xml(self, options):
        xml_content = self.env["ir.qweb"]._render("l10n_it_xml_export.tax_report_export_template", self._get_xml_export_data(options))
        xml_content = Markup("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>""") + xml_content
        xml_content = xml_content.encode()

        with file_open("l10n_it_xml_export/data/validation/fornituraIvp_2018_v1.xsd", 'rb') as xsd:
            xsd_schema = etree.XMLSchema(etree.parse(xsd))
            try:
                xsd_schema.assertValid(etree.fromstring(xml_content))
            except etree.DocumentInvalid as xml_errors:
                self.env['bus.bus']._sendone(
                    self.env.user.partner_id,
                    'simple_notification',
                    {
                        'type': 'warning',
                        'title': _('XML Validation Error'),
                        'message': _(
                            "Some values will not pass the authority's validation, please check them before submitting your file: %s",
                            [error.path.split(":")[-1] for error in xml_errors.error_log]
                        ),
                        'sticky': True,
                    },
                )

        return {
            "file_name": self.env["account.report"].browse(options["report_id"]).get_default_report_filename(options, 'xml'),
            "file_content": xml_content,
            "file_type": "xml",
        }

    def _get_xml_export_data(self, options):
        options_date_to = fields.Date.from_string(options["date"]["date_to"])
        report = self.env["account.report"].browse(options["report_id"])
        company = report._get_sender_company_for_export(options)
        report_lines = report._get_lines(options)
        colname_to_idx = {col['expression_label']: idx for idx, col in enumerate(options.get('columns', []))}
        report_line2amount = {
            line['columns'][colname_to_idx['balance']]['report_line_id']: (
                "{:.2f}".format(
                    float(line['columns'][colname_to_idx['balance']]['no_format'])
                ).replace(".", ",")
                if line['columns'][colname_to_idx['balance']]['no_format'] else
                False
            )
            for line in report_lines
        }
        report_lines_data = {}
        for report_line in self.env['account.report.line'].browse(report_line2amount.keys()):
            report_lines_data[report_line.code] = report_line2amount[report_line.id]

        # VP6a and VP6b values must be absolute values.
        for code in ["VP6a", "VP6b"]:
            if report_lines_data[code] and report_lines_data[code][0] == "-":
                report_lines_data[code] = report_lines_data[code][1:]

        return {
            "supply_code": "IVP18",
            "declarant_fiscal_code": options["declarant_fiscal_code"],
            "declarant_role_code": options["declarant_role_code"],
            "id_sistema": options["id_sistema"],
            "taxpayer_code": company.l10n_it_codice_fiscale,
            "tax_year": options_date_to.year,
            "vat_number": "".join([char for char in report.get_vat_for_export(options) if char.isdigit()]),
            "parent_company_vat_number": options["parent_company_vat_number"],
            "last_month": (options_date_to - relativedelta(months=1)).month,
            "company_code": options["company_code"],
            "intermediary_code": options["intermediary_code"],
            "submission_commitment": options["intermediary_code"] and int(options["submission_commitment"]),
            "commitment_date": options["intermediary_code"] and fields.Date.from_string(options["commitment_date"]).strftime("%d%m%Y"),
            "intermediary_signature": options["intermediary_code"] and 1,
            "month": options_date_to.month,
            "subcontracting": options["subcontracting"] and 1,
            "exceptional_events": options["exceptional_events"] and 1,
            "extraordinary_operations": options["extraordinary_operations"] and 1,
            "total_active_operations": report_lines_data["VP2"],
            "total_passive_operations": report_lines_data["VP3"],
            "vat_payable": report_lines_data["VP4"],
            "vat_deducted": report_lines_data["VP5"],
            "vat_due": report_lines_data["VP6a"],
            "vat_credit": report_lines_data["VP6b"],
            "previous_debt": report_lines_data["VP7"],
            "previous_period_credit": report_lines_data["VP8"],
            "previous_year_credit": report_lines_data["VP9"],
            "eu_self_payments": report_lines_data["VP10"],
            "tax_credits": report_lines_data["VP11"],
            "due_interests": report_lines_data["VP12"],
            "method": int(options["method"]),
            "advance_payment": report_lines_data["VP13"],
            "amount_to_be_paid": report_lines_data["VP14a"],
            "amount_in_credit": report_lines_data["VP14b"],
        }
