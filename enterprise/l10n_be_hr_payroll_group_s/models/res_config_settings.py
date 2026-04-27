# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # "group" is prohibited by the framework
    gr_s_code = fields.Char(
        related='company_id.group_s_code',
        readonly=False)
