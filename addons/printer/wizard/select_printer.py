# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SelectPrinterWizard(models.TransientModel):
    _name = 'select.printer.wizard'
    _description = "Selection of printers for printing a report"

    printer_ids = fields.Many2many('printer.printer', string="Select Printers", domain="[('id', 'in', display_printer_ids)]")
    display_printer_ids = fields.Many2many('printer.printer', relation='display_printer_id_select_printer', default=lambda self: self.env['printer.printer'].search([]).ids)
    do_not_ask_again = fields.Boolean("Don't ask me again", help="If checked, this dialog won't appear the next time you print and the selected printers will be used automatically.")
    download_pdf = fields.Boolean("Download PDF", help="If checked, It will Download PDF instead printing it.")
