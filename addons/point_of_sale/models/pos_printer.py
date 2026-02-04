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
        default='epson_epos',
        selection=[
            ('epson_epos', 'IP address'),
        ]
    )
    printer_type_count = fields.Integer(
        string="Printer Type Count",
        compute="_compute_printer_type_count",
    )
    use_type = fields.Selection(selection=[
        ('preparation', "Preparation"),
        ('receipt', "Receipt"),
    ], string="Type", default="preparation")
    product_categories_ids = fields.Many2many('pos.category', 'printer_category_rel', 'printer_id', 'category_id', string='Printed Product Categories')
    pos_config_ids = fields.Many2many('pos.config', 'pos_config_receipt_printer_rel', 'printer_id', 'config_id', string="Point of Sale")
    epson_printer_ip = fields.Char(
        string='Epson Printer IP Address',
        help=(
            "Local IP address of an Epson receipt printer, or its serial number if the "
            "'Automatic Certificate Update' option is enabled in the printer settings."
        ),
    )
    use_lna = fields.Boolean(string="Use Local Network Access")

    def copy_data(self, default=None):
        default = dict(default or {}, pos_config_ids=[(5, 0, 0)], epson_printer_ip="0.0.0.0")
        vals_list = super().copy_data(default=default)
        if 'name' not in default:
            for printer, vals in zip(self, vals_list):
                vals['name'] = _("%s (copy)", printer.name)
        return vals_list

    def _compute_printer_type_count(self):
        self.printer_type_count = len(self._fields['printer_type'].selection)

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('id', 'in', config.preparation_printer_ids.ids + config.receipt_printer_ids.ids)]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'product_categories_ids', 'printer_type', 'use_type', 'use_lna', 'epson_printer_ip']

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
