# ©  2015-2020 Deltatech
# See README.rst file on addons root folder for license details

import time

from odoo import api, models


class ReportDCPrint(models.AbstractModel):
    _name = "report.deltatech_dc.report_dc"
    _description = "ReportDCPrint"
    _template = "deltatech_dc.report_dc"

    @api.model
    def _get_report_values(self, docids, data=None):
        report = self.env["ir.actions.report"]._get_report_from_name(self._template)
        return {
            "doc_ids": docids,
            "doc_model": report.model,
            "data": data,
            "time": time,
            "docs": self.env[report.model].browse(docids),
            "lot": False,
        }


class ReportDCLotPrint(models.AbstractModel):
    _name = "report.deltatech_dc.report_dc_lot"
    _description = "ReportDCPrint"
    _template = "deltatech_dc.report_dc_lot"

    @api.model
    def _get_report_values(self, docids, data=None):
        report = self.env["ir.actions.report"]._get_report_from_name(self._template)
        return {
            "doc_ids": docids,
            "doc_model": report.model,
            "data": data,
            "time": time,
            "docs": self.env[report.model].browse(docids),
            "lot": True,
        }


class ReportDCInvoicePrint(models.AbstractModel):
    _name = "report.deltatech_dc.report_dc_invoice"
    _description = "ReportDCPrint"
    _template = "deltatech_dc.report_dc_invoice"

    @api.model
    def _get_report_values(self, docids, data=None):
        report = self.env["ir.actions.report"]._get_report_from_name(self._template)
        # care sunt livrarile aferente acestie facturi ?????

        invoices = self.env[report.model].browse(docids)

        declarations = self.env["deltatech.dc"]

        for invoice in invoices.filtered(lambda x: x.state not in ["draft", "cancel"]):
            for line in invoice.invoice_line_ids:
                domain = [("product_id", "=", line.product_id.id), ("date", "=", invoice.date)]
                dc = self.env["deltatech.dc"].search(domain)
                if not dc:
                    dc = self.env["deltatech.dc"].create(
                        {"name": invoice.name, "product_id": line.product_id.id, "date": invoice.date}
                    )
                declarations |= dc

        return {
            "doc_ids": declarations.ids,
            "doc_model": "deltatech.dc",
            "data": data,
            "time": time,
            "docs": declarations,
            "lot": False,
        }
