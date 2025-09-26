# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.addons.pos_epson_printer.models.pos_config import format_epson_certified_domain


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_epson_printer_ip = fields.Char(compute='_compute_pos_epson_printer_ip', store=True, readonly=False)

    @api.depends('pos_epson_printer_ip', 'pos_other_devices')
    def _compute_pos_iface_cashdrawer(self):
        """We are just adding depends on this compute."""
        super()._compute_pos_iface_cashdrawer()

    def _is_cashdrawer_displayed(self, res_config):
        return super()._is_cashdrawer_displayed(res_config) or (res_config.pos_other_devices and bool(res_config.pos_epson_printer_ip))

    @api.depends('pos_other_devices', 'pos_config_id')
    def _compute_pos_epson_printer_ip(self):
        for res_config in self:
            if not res_config.pos_other_devices:
                res_config.pos_epson_printer_ip = ''
            else:
                res_config.pos_epson_printer_ip = res_config.pos_config_id.epson_printer_ip

    @api.onchange("pos_epson_printer_ip")
    def _onchange_epson_printer_ip(self):
        for rec in self:
            if rec.pos_epson_printer_ip:
                rec.pos_epson_printer_ip = format_epson_certified_domain(rec.pos_epson_printer_ip)
