# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models

class LoyaltyProgram(models.Model):
    _inherit = 'loyalty.program'

    @api.model
    def _program_type_default_values(self):
        res = super()._program_type_default_values()
        # Add a loyalty reward for free shipping
        if 'loyalty' in res:
            res['loyalty']['reward_ids'].append((0, 0, {
                'reward_type': 'shipping',
                'required_points': 100,
            }))
        return res

    @api.model
    def get_program_templates(self):
        # Override 'promotion' template to say free shipping
        res = super().get_program_templates()
        if 'promotion' in res:
            res['promotion']['description'] = _("Automatic promotion: free shipping on orders higher than $50")
        return res

    @api.model
    def _get_template_values(self):
        res = super()._get_template_values()
        if 'promotion' in res:
            res['promotion']['reward_ids'] = [(5, 0, 0), (0, 0, {
                'reward_type': 'shipping',
            })]
        return res
