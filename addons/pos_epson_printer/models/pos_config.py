# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.pos_epson_printer.models.pos_printer import format_epson_certified_domain


class PosConfig(models.Model):
    _inherit = 'pos.config'

    epson_printer_ip = fields.Char(
        string='Epson Printer IP',
        help=(
             "Local IP address of an Epson receipt printer, or its serial number if the "
             "'Automatic Certificate Update' option is enabled in the printer settings."
        )
    )

    @api.onchange("epson_printer_ip")
    def _onchange_epson_printer_ip(self):
        for rec in self:
            if rec.epson_printer_ip:
                rec.epson_printer_ip = format_epson_certified_domain(rec.epson_printer_ip)
