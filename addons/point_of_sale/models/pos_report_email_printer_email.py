# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosReportEmailPrinterEmail(models.Model):
    _name = "pos.report_email_printer_email"
    _rec_name = "email"
    _description = "Email address for a report email printer"

    email = fields.Char("Email address", required=True)

    _sql_constraints = [("email_unique", "unique (email)", "A printer with this email has already been added.")]
