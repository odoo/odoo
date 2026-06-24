# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    last_lunch_location_id = fields.Many2one('lunch.location', groups='lunch.group_lunch_user', copy=False)
    favorite_lunch_product_ids = fields.Many2many('lunch.product', 'lunch_product_favorite_user_rel', 'user_id', 'product_id', groups='lunch.group_lunch_user', copy=False)

    @api.model
    def _get_maximal_light_user_groups(self):
        groups = super()._get_maximal_light_user_groups()
        group = self.env.ref('lunch.group_lunch_user', raise_if_not_found=False)
        return groups | group if group else groups
