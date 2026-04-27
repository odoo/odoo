from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_module_pos_urban_piper = fields.Boolean(related='pos_config_id.module_pos_urban_piper', string="Urban Piper", help="Manage your online orders with Urban Piper.", readonly=False)
