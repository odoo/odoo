# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = ['res.config.settings']

    hr_recruitment_monster_username = fields.Char(
        related="company_id.hr_recruitment_monster_username",
        readonly=False,
    )
    hr_recruitment_monster_password = fields.Char(
        related="company_id.hr_recruitment_monster_password",
        readonly=False,
    )
