# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_it_fiscal_printer_https = fields.Boolean(related='pos_config_id.it_fiscal_printer_https', readonly=False)
    pos_it_fiscal_printer_ip = fields.Char(related='pos_config_id.it_fiscal_printer_ip', readonly=False)
    pos_it_fiscal_cash_drawer = fields.Boolean(related='pos_config_id.it_fiscal_cash_drawer', readonly=False)
