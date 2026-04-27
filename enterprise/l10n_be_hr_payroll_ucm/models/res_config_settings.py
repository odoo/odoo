# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ucm_code = fields.Char(
        related='company_id.ucm_code', string="UCM Affiliation Number", readonly=False)
    ucm_company_code = fields.Char(
        related='company_id.ucm_company_code', string="UCM Company Code", readonly=False)
