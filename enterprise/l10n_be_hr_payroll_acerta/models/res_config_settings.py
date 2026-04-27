# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    acerta_code = fields.Char(
        related='company_id.acerta_code', string="Acerta Affiliation Number", readonly=False)
