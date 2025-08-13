# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


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
    epson_printer_ip = fields.Char(string='Epson Printer IP Address', help="Local IP address of an Epson receipt printer.", default="0.0.0.0")

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('id', 'in', config.printer_ids.ids)]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'proxy_ip', 'product_categories_ids', 'printer_type', 'epson_printer_ip']

    @api.constrains('epson_printer_ip')
    def _constrains_epson_printer_ip(self):
        for record in self:
            if record.printer_type == 'epson_epos' and not record.epson_printer_ip:
                raise ValidationError(_("Epson Printer IP Address cannot be empty."))
