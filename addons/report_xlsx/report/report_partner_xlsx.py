# Copyright 2017 Creu Blanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class PartnerXlsx(models.AbstractModel):
    _name = "report.report_xlsx.partner_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Partner XLSX Report"

    def generate_xlsx_report(self, workbook, data, partners):
        sheet = workbook.add_worksheet("Report")
        for i, obj in enumerate(partners):
            bold = workbook.add_format({"bold": True})
            sheet.write(i, 0, obj.name, bold)
