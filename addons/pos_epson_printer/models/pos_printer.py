# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b32encode
from hashlib import sha256
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


def format_epson_certified_domain(serial_number):
    """Epson printers can be configured to use a wildcard certificate,
    for a domain name derived from the printer serial number.

    :param serial_number: The printer serial number or an IP address.
    :return: The corresponding domain name, or the original IP address.
    """
    if "." in serial_number:
        # If the field is provided an epson serial number, convert it to a domain name
        # Note: serial numbers should not contain dots, as IPs or URLs would.
        return serial_number

    epson_domain = "omnilinkcert.epson.biz"

    sha256_hash = sha256(serial_number.encode()).digest()
    base32_text = b32encode(sha256_hash).decode().rstrip("=")
    return f"{base32_text.lower()}.{epson_domain}"


class PosPrinter(models.Model):

    _inherit = 'pos.printer'

    printer_type = fields.Selection(selection_add=[('epson_epos', 'Use an Epson printer')])
    epson_printer_ip = fields.Char(
        string='Epson Printer IP Address',
        help=(
            "Local IP address of an Epson receipt printer, or its serial number if the "
            "'Automatic Certificate Update' option is enabled in the printer settings."
        ),
        default="0.0.0.0"
    )

    @api.constrains('epson_printer_ip')
    def _constrains_epson_printer_ip(self):
        for record in self:
            if record.printer_type == 'epson_epos' and not record.epson_printer_ip:
                raise ValidationError(_("Epson Printer IP Address cannot be empty."))

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ['epson_printer_ip']
        return params

    @api.onchange("epson_printer_ip")
    def _onchange_epson_printer_ip(self):
        for rec in self:
            if rec.epson_printer_ip:
                rec.epson_printer_ip = format_epson_certified_domain(rec.epson_printer_ip)
