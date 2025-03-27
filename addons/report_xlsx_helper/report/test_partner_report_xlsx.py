# Copyright 2009-2019 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from .report_xlsx_format import FORMATS, XLS_HEADERS


# TODO:
# make PR to move this class as well as the report_xlsx test class
# to the tests folder (requires dynamic update Odoo registry when
# running unit tests.
class TestPartnerXlsx(models.AbstractModel):
    _name = "report.report_xlsx_helper.test_partner_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Test Partner XLSX Report"

    def _get_ws_params(self, wb, data, partners):

        partner_template = {
            "name": {
                "header": {"value": "Name"},
                "data": {"value": self._render("partner.name")},
                "width": 20,
            },
            "number_of_contacts": {
                "header": {"value": "# Contacts"},
                "data": {"value": self._render("len(partner.child_ids)")},
                "width": 10,
            },
            "date": {
                "header": {"value": "Date"},
                "data": {"value": self._render("partner.date")},
                "width": 13,
            },
        }

        ws_params = {
            "ws_name": "Partners",
            "generate_ws_method": "_partner_report",
            "title": "Partners",
            "wanted_list": [k for k in partner_template],
            "col_specs": partner_template,
        }

        return [ws_params]

    def _partner_report(self, workbook, ws, ws_params, data, partners):

        ws.set_portrait()
        ws.fit_to_pages(1, 0)
        ws.set_header(XLS_HEADERS["xls_headers"]["standard"])
        ws.set_footer(XLS_HEADERS["xls_footers"]["standard"])
        self._set_column_width(ws, ws_params)

        row_pos = 0
        row_pos = self._write_ws_title(ws, row_pos, ws_params)
        row_pos = self._write_line(
            ws,
            row_pos,
            ws_params,
            col_specs_section="header",
            default_format=FORMATS["format_theader_yellow_left"],
        )
        ws.freeze_panes(row_pos, 0)

        for partner in partners:
            row_pos = self._write_line(
                ws,
                row_pos,
                ws_params,
                col_specs_section="data",
                render_space={"partner": partner},
                default_format=FORMATS["format_tcell_left"],
            )
