# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    external_code = fields.Char(
        related='company_id.external_code', string="External Code", readonly=False)
    work_entry_source = fields.Selection(string='Default Tracking', related='company_id.work_entry_source',
                                         groups="hr.group_hr_user", readonly=False)
