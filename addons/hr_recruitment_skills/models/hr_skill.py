# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrSkill(models.Model):
    _inherit = 'hr.skill'

    missing_color = fields.Integer(
        default=1,  # TODO: This is not a smart approach :D
    )
    matching_color = fields.Integer(
        default=10,  # TODO: This is not a smart approach :D
    )
