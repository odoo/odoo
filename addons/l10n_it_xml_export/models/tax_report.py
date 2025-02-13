from markupsafe import Markup

from odoo import _, fields, models


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
        })

    def print_tax_report_to_xml(self, options):
        new_wizard = self.env['l10n_it_xml_export.monthly.tax.report.xml.export.wizard'].create({})
        view_id = self.env.ref('l10n_it_xml_export.monthly_tax_report_xml_export_wizard_view').id
        return {
            'name': _('XML Export Options'),
            'view_mode': 'form',
            'views': [[view_id, 'form']],
            'res_model': 'l10n_it_xml_export.monthly.tax.report.xml.export.wizard',
            'type': 'ir.actions.act_window',
            'res_id': new_wizard.id,
            'target': 'new',
            'context': dict(self._context, l10n_it_xml_export_monthly_tax_report_options=options),
        }

    def export_tax_report_to_xml(self, options):
        xml_content = self.env["ir.qweb"]._render("l10n_it_xml_export.tax_report_export_template", self._get_xml_export_data(options))
        xml_content = Markup("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>""") + xml_content
        return {
            "file_name": self.env["account.report"].browse(options["report_id"]).get_default_report_filename(options, 'xml'),
            "file_content": xml_content.encode(),
            "file_type": "xml",
        }

    def _get_xml_export_data(self, options):
        options_date_to = fields.Date.from_string(options["date"]["date_to"])
        report = self.env["account.report"].browse(options["report_id"])
        company = report._get_sender_company_for_export(options)
        report_lines = report._get_lines(options)
        colname_to_idx = {col['expression_label']: idx for idx, col in enumerate(options.get('columns', []))}
        lines_mapping = {
            line['columns'][colname_to_idx['balance']]['report_line_id']: line['columns'][colname_to_idx['balance']]['no_format'] or 0 for line in report_lines
        }
        report_lines_data = {}
        for record in self.env['account.report.line'].browse(lines_mapping.keys()):
            report_lines_data[record.code] = lines_mapping[record.id]

        return {
            "supply_code": "IVP18",
            "declarant_fiscal_code": options.get("declarant_fiscal_code"),
            "charging_code": options.get("charging_code"),
            "id_sistema": options.get("id_sistema"),
            "taxpayer_code": company.l10n_it_codice_fiscale,
            "tax_year": options_date_to.year,
            "vat_number": report.get_vat_for_export(options),
            "parent_vat_number": options.get("parent_vat_number"),
            "last_month": options_date_to.month == 12 and 1 or 0,
            "declarant_code": options.get("declarant_code"),
            "declarant_role_code": options.get("declarant_role_code"),
            "intermediary_code": options.get("intermediary_code"),
            "submission_commitment": options.get("intermediary_code") and int(options.get("submission_commitment")),
            "commitment_date": options.get("intermediary_code") and fields.Date.from_string(options.get("commitment_date")),
            "intermediary_signature": options.get("intermediary_code") and 1,
            "module_number": options.get("module_number") or 1,
            "month": options_date_to.month,
            "subcontracting": options.get("subcontracting") and 1,
            "exceptional_events": options.get("exceptional_events") and 1,
            "extraordinary_operations": options.get("extraordinary_operations") and 1,
            "total_active_operations": report_lines_data["VP2"],
            "total_passive_operations": report_lines_data["VP3"],
            "vat_payable": report_lines_data["VP4"],
            "vat_deducted": report_lines_data["VP5"],
            "vat_due": abs(report_lines_data["VP6a"]),
            "vat_credit": abs(report_lines_data["VP6b"]),
            "previous_debt": report_lines_data["VP7"],
            "previous_period_credit": report_lines_data["VP8"],
            "previous_year_credit": report_lines_data["VP9"],
            "eu_self_payments": report_lines_data["VP10"],
            "tax_credits": report_lines_data["VP11"],
            "due_interests": report_lines_data["VP12"],
            "method": int(options.get("method")),
            "advance_payment": report_lines_data["VP13"],
            "amount_to_be_paid": report_lines_data["VP14a"],
            "amount_in_credit": report_lines_data["VP14b"],
        }
