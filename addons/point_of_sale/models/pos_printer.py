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


EPSON_MODELS = [
    ('tm_t88_80', 'TM-T88 series (80mm)'),
    ('tm_t88_58', 'TM-T88 series (58mm)'),
    ('tm_t70_80', 'TM-T70 series (80mm)'),
    ('tm_t70_58', 'TM-T70 series (58mm)'),
    ('tm_t70_80', 'TM-T70 series (Multi-language, 80mm)'),
    ('tm_t70_58', 'TM-T70 series (Multi-language, 58mm)'),
    ('tm_t90_80', 'TM-T90 series (80mm)'),
    ('tm_t90_58', 'TM-T90 series (58mm)'),
    ('tm_t90_kp', 'TM-T90KP (80mm)'),
    ('tm_l90_re', 'TM-L90 (Receipt)'),
    ('tm_l90_la', 'TM-L90 (Label)'),
    ('tm_l100_80', 'TM-L100 series (80mm)'),
    ('tm_l100_58', 'TM-L100 series (58mm)'),
    ('tm_l100_40', 'TM-L100 series (40mm)'),
    ('tm_p60_60', 'TM-P60 series (60mm)'),
    ('tm_p60_58', 'TM-P60 series (58mm)'),
    ('tm_p60_la', 'TM-P60 series (Label)'),
    ('tm_p80_48', 'TM-P80 series (80mm)'),
    ('tm_p80_42', 'TM-P80 series (80mm, 42 column mode)'),
    ('tm_p80ii_80_48', 'TM-P80II series (80mm)'),
    ('tm_p80ii_80_42', 'TM-P80II series (80mm, 42 column mode)'),
    ('tm_p80ii_58', 'TM-P80II series (58mm)'),
    ('tm_p20_58', 'TM-P20 series (58mm)'),
    ('tm_t20_80', 'TM-T20 series (80mm)'),
    ('tm_t20_58', 'TM-T20 series (58mm)'),
    ('tm_m10_58', 'TM-m10 series (58mm)'),
    ('tm_m30_80', 'TM-m30 series (80mm)'),
    ('tm_m30_58', 'TM-m30 series (58mm)'),
    ('tm_m50_80', 'TM-m50 series (80mm)'),
    ('tm_m50_58', 'TM-m50 series (58mm)'),
    ('tm_m55_80', 'TM-m55 series (80mm)'),
    ('tm_m55_58', 'TM-m55 series (58mm)'),
    ('tm_t82_80', 'TM-T82 series (80mm)'),
    ('tm_t82_58', 'TM-T82 series (58mm)'),
    ('tm_t83_80', 'TM-T83 series (80mm)'),
    ('tm_t83_58', 'TM-T83 series (58mm)'),
    ('tm_u22_76', 'TM-U220 series (76mm)'),
    ('tm_u22_70', 'TM-U220 series (70mm)'),
    ('tm_u22_58', 'TM-U220 series (58mm)'),
    ('tm_u33_76', 'TM-U330 series (76mm)'),
    ('tm_u33_70', 'TM-U330 series (70mm)'),
    ('tm_u33_58', 'TM-U330 series (58mm)'),
    ('tm_h60_re', 'TM-H6000  series (Receipt)'),
]


class PosPrinter(models.Model):
    _name = 'pos.printer'

    _description = 'Point of Sale Printer'
    _inherit = ['pos.load.mixin']

    name = fields.Char('Printer Name', required=True, default='Printer', help='An internal identification of the printer')
    printer_type = fields.Selection(
        string='Printer Type',
        default='epson_epos',
        selection=[
            ('epson_epos', 'ePoS'),
        ]
    )
    use_type = fields.Selection(selection=[
        ('preparation', "Preparation"),
        ('receipt', "Receipt"),
    ], string="Type", default="preparation")
    product_categories_ids = fields.Many2many('pos.category', 'printer_category_rel', 'printer_id', 'category_id', string='Printed Product Categories')
    pos_config_ids = fields.Many2many('pos.config', 'pos_config_receipt_printer_rel', 'printer_id', 'config_id', string="Point of Sale")
    printer_ip = fields.Char(
        string='Epson Printer IP Address',
        help=(
            "Local IP address of an Epson receipt printer, or its serial number if the "
            "'Automatic Certificate Update' option is enabled in the printer settings."
        ),
    )
    use_lna = fields.Boolean(string="Use Local Network Access")
    paper_size = fields.Selection(string="Paper Size", selection=[
        ('80', 'Standard 80mm'),
        ('58', 'Standard 58mm'),
        *EPSON_MODELS,
    ], required=True, default='80')
    paper_size_keys = fields.Char(compute='_compute_paper_size_keys')
    timeout = fields.Integer(string="Connection Timeout (ms)", default=3000, help="Time in milliseconds before considering that the printer is not responding.")

    def copy_data(self, default=None):
        default = dict(default or {}, pos_config_ids=[(5, 0, 0)], printer_ip="0.0.0.0")
        vals_list = super().copy_data(default=default)
        if 'name' not in default:
            for printer, vals in zip(self, vals_list):
                vals['name'] = _("%s (copy)", printer.name)
        return vals_list

    @api.depends('printer_type')
    def _compute_paper_size_keys(self):
        for record in self:
            standard_size = ['58', '80']

            if record.printer_type == 'epson_epos':
                epson_models = [key for key, _ in EPSON_MODELS]
                standard_size.extend(epson_models)

            record.paper_size_keys = ",".join(standard_size)

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('id', 'in', config.preparation_printer_ids.ids + config.receipt_printer_ids.ids)]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'product_categories_ids', 'printer_type', 'use_type', 'use_lna', 'printer_ip', 'paper_size', 'timeout']

    @api.constrains('printer_ip')
    def _constrains_printer_ip(self):
        for record in self:
            if record.printer_type == 'epson_epos' and not record.printer_ip:
                raise ValidationError(_("Printer IP Address cannot be empty."))

    @api.onchange("printer_ip")
    def _onchange_printer_ip(self):
        for rec in self:
            if rec.printer_ip:
                rec.printer_ip = format_epson_certified_domain(rec.printer_ip)

    @api.onchange('printer_type')
    def _onchange_printer_type(self):
        for rec in self:
            if rec.paper_size not in rec.paper_size_keys.split(","):
                rec.paper_size = '80'
