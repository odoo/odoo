# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Printer(models.Model):
    _name = 'printer.printer'
    _description = 'Printer'

    name = fields.Char(string="Name", required=True)
    printer_ip = fields.Char(
        string="Printer IP",
        required=True,
        help="Provide the IP address of the printer. You can find this in the application used to manage and detect printers.",
    )
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    printer_type = fields.Selection([
            ('office_printer', "Office Printer"),
        ],
        string="Printer Type",
        default='office_printer',
        help=(
            "Select the printer type to control formatting and printing behavior:\n"
            "- Office Printer: For standard documents such as PDF reports.\n"
        ),
    )
    report_ids = fields.Many2many(
        'ir.actions.report',
        'report_printer_rel',
        'printer_id',
        'report_id',
        string="Reports",
        help="Choose the reports that can be printed with this printer.",
    )
