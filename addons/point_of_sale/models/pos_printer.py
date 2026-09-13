from base64 import b32encode
from hashlib import sha256

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ..tools import debug_log as dbg


def format_epson_certified_domain(serial_number):
    if "." in serial_number:
        return serial_number

    epson_domain = "omnilinkcert.epson.biz"

    sha256_hash = sha256(serial_number.encode()).digest()
    base32_text = b32encode(sha256_hash).decode().rstrip("=")
    dbg.logic.debug("epson serial %r -> certified domain", serial_number)
    return f"{base32_text.lower()}.{epson_domain}"


class PosPrinter(models.Model):
    _name = "pos.printer"

    _description = "Point of Sale Printer"
    _inherit = ["mixin.pos.load"]

    name = fields.Char(
        string="Printer Name",
        default="Printer",
        required=True,
        help="An internal identification of the printer",
    )
    printer_type = fields.Selection(
        selection=[
            ("iot", "Use a printer connected to the IoT Box"),
            ("epson_epos", "Use an Epson printer"),
        ],
        default="iot",
    )
    proxy_ip = fields.Char(
        string="Proxy IP Address",
        help="The IP Address or hostname of the Printer's hardware proxy",
    )
    product_categories_ids = fields.Many2many(
        comodel_name="pos.category",
        relation="printer_category_rel",
        column1="printer_id",
        column2="category_id",
        string="Printed Product Categories",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    pos_config_ids = fields.Many2many(
        comodel_name="pos.config",
        relation="pos_config_printer_rel",
        column1="printer_id",
        column2="config_id",
    )
    epson_printer_ip = fields.Char(
        string="Epson Printer IP Address",
        default="0.0.0.0",
        help="Local IP address of an Epson receipt printer, or its serial number if the "
        "'Automatic Certificate Update' option is enabled in the printer settings.",
    )

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [("id", "in", config.printer_ids.ids)]

    @api.model
    def _load_pos_data_fields(self, config):
        return [
            "id",
            "name",
            "proxy_ip",
            "product_categories_ids",
            "printer_type",
            "epson_printer_ip",
        ]

    @api.model
    def use_local_network_access(self):
        use_lna = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param_bool("point_of_sale.use_lna")
        )
        return {"use_lna": use_lna}

    @api.constrains("epson_printer_ip")
    def _constrains_epson_printer_ip(self):
        for record in self:
            if record.printer_type == "epson_epos" and not record.epson_printer_ip:
                raise ValidationError(_("Epson Printer IP Address cannot be empty."))

    @api.onchange("epson_printer_ip")
    def _onchange_epson_printer_ip(self):
        for rec in self:
            if rec.epson_printer_ip:
                rec.epson_printer_ip = format_epson_certified_domain(
                    rec.epson_printer_ip
                )
