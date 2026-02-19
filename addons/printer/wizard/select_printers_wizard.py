# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SelectPrintersWizard(models.TransientModel):
    _name = 'select.printers.wizard'
    _description = "Select printers to print the report on"

    printer_ids = fields.Many2many(
        "printer.printer",
        domain="[('id', 'in', context.get('available_printer_ids', []))]",
    )
    do_not_ask_again = fields.Boolean(
        "Do not ask me again",
        help=(
            "If checked, this dialog won't appear the next time you print "
            "and the selected printers will be used automatically."
        ),
    )
