# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosReportEmailPrinter(models.Model):
    _name = "pos.report_email_printer"
    _description = "Report Email Printer"

    report_id = fields.Many2one("ir.actions.report", required=True)
    email_ids = fields.Many2many("pos.report_email_printer_email")

    _sql_constraints = [("report_id_unique", "unique (report_id)", "A record already exists for this report.")]
