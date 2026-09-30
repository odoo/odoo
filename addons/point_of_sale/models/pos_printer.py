# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b32encode
from hashlib import sha256
from odoo import api, fields, models, _
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
    _name = 'pos.printer'

    _description = 'Point of Sale Printer'
    _inherit = ['pos.load.mixin']

    name = fields.Char('Printer Name', required=True, default='Printer', help='An internal identification of the printer')
    printer_type = fields.Selection(
        string='Printer Type',
        default='iot',
        selection=[
            ('iot', 'Use a printer connected to the IoT Box'),
            ('epson_epos', 'Use an Epson printer'),
        ]
    )
    proxy_ip = fields.Char('Proxy IP Address', help="The IP Address or hostname of the Printer's hardware proxy")
    product_categories_ids = fields.Many2many('pos.category', 'printer_category_rel', 'printer_id', 'category_id', string='Printed Product Categories')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    pos_config_ids = fields.Many2many('pos.config', 'pos_config_printer_rel', 'printer_id', 'config_id')
    epson_printer_ip = fields.Char(
        string='Epson Printer IP Address',
        help=(
            "Local IP address of an Epson receipt printer, or its serial number if the "
            "'Automatic Certificate Update' option is enabled in the printer settings."
        ),
        default="0.0.0.0"
    )

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('id', 'in', config.printer_ids.ids)]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'proxy_ip', 'product_categories_ids', 'printer_type', 'epson_printer_ip']

    @api.model
    def use_local_network_access(self):
        use_lna = bool(self.env['ir.config_parameter'].sudo().get_param('point_of_sale.use_lna'))
        return {
            'use_lna': use_lna
        }

    @api.constrains('epson_printer_ip')
    def _constrains_epson_printer_ip(self):
        for record in self:
            if record.printer_type == 'epson_epos' and not record.epson_printer_ip:
                raise ValidationError(_("Epson Printer IP Address cannot be empty."))

    @api.onchange("epson_printer_ip")
    def _onchange_epson_printer_ip(self):
        for rec in self:
            if rec.epson_printer_ip:
                rec.epson_printer_ip = format_epson_certified_domain(rec.epson_printer_ip)
