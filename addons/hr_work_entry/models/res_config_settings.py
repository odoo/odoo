# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    external_code = fields.Char(
        related='company_id.external_code', string="External Code", readonly=False)
