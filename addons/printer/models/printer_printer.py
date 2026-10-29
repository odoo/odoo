# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError

# A host name, an IPv4 address or a bracketed IPv6 address, optionally followed
# by a port and a path: "192.168.1.20", "zebra-1.local:8080", "[fe80::1]/epos".
ADDRESS_RE = re.compile(r'^(\[[0-9a-fA-F:.]+\]|[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?)(:\d{1,5})?(/\S*)?$')


class PrinterPrinter(models.Model):
    _name = 'printer.printer'
    _description = "Printer"
    _order = 'name, id'

    name = fields.Char(required=True)
    address = fields.Char(
        required=True,
        help="IP address or host name of the printer on the local network, optionally with a port or a path, "
             "e.g. 192.168.1.20 or zebra-1.local:8080")
    kind = fields.Selection(
        [('zpl', "ZPL"), ('epos', "ePOS")], required=True, default='zpl',
        help="ZPL: Zebra label printers, they print the ZPL text reports.\n"
             "ePOS: Epson thermal printers, they print the PDF reports as images.")
    report_ids = fields.Many2many(
        'ir.actions.report', 'printer_printer_ir_actions_report_rel', 'printer_id', 'report_id',
        string="Reports", help="Reports sent to this printer when they are printed.")

    @api.depends('name', 'kind')
    @api.depends_context('printer_show_kind')
    def _compute_display_name(self):
        if not self.env.context.get('printer_show_kind'):
            super()._compute_display_name()
            return
        kinds = dict(self._fields['kind']._description_selection(self.env))
        for printer in self:
            printer.display_name = self.env._("%(kind)s - %(name)s", kind=kinds.get(printer.kind), name=printer.name)

    @api.constrains('address')
    def _check_address(self):
        for printer in self:
            if printer.address and not ADDRESS_RE.match(printer.address):
                raise ValidationError(self.env._(
                    "The address of the printer %(printer)s must be an IP address or a host name, optionally "
                    "with a port or a path, without protocol (e.g. 192.168.1.20 or zebra-1.local:8080).",
                    printer=printer.name,
                ))
