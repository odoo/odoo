# Copyright  2018 Forest and Biomass Romania
# Copyright 2021 Tecnativa - João Marques
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, models


class VATReportXslx(models.AbstractModel):
    _name = "report.a_f_r.report_vat_report_xlsx"
    _description = "Vat Report XLSX Report"
    _inherit = "report.account_financial_report.abstract_report_xlsx"

    def _get_report_name(self, report, data):
        company_id = data.get("company_id", False)
        report_name = _("Vat Report")
        if company_id:
            company = self.env["res.company"].browse(company_id)
            suffix = f" - {company.name} - {company.currency_id.name}"
            report_name = report_name + suffix
        return report_name

    def _get_report_columns(self, report):
        return {
            0: {"header": _("Code"), "field": "code", "width": 5},
            1: {"header": _("Name"), "field": "name", "width": 100},
            2: {"header": _("Net"), "field": "net", "type": "amount", "width": 14},
            3: {"header": _("Tax"), "field": "tax", "type": "amount", "width": 14},
        }

    def _get_report_filters(self, report):
        return [
            [_("Date from"), report.date_from.strftime("%d/%m/%Y")],
            [_("Date to"), report.date_to.strftime("%d/%m/%Y")],
            [
                _("Based on"),
                _("Tax Tags") if report.based_on == "taxtags" else _("Tax Groups"),
            ],
        ]

    def _get_col_count_filter_name(self):
        return 0

    def _get_col_count_filter_value(self):
        return 2

    def _generate_report_content(self, workbook, report, data, report_data):
        res_data = self.env[
            "report.account_financial_report.vat_report"
        ]._get_report_values(report, data)
        vat_report = res_data["vat_report"]
        tax_detail = res_data["tax_detail"]
        # For each tax_tag tax_group
        self.write_array_header(report_data)
        for tag_or_group in vat_report:
            # Write taxtag line
            self.write_line_from_dict(tag_or_group, report_data)

            # For each tax if detail taxes
            if tax_detail:
                for tax in tag_or_group["taxes"]:
                    self.write_line_from_dict(tax, report_data)
