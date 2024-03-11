# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    last_lunch_location_id = fields.Many2one('lunch.location')
    favorite_lunch_product_ids = fields.Many2many('lunch.product', 'lunch_product_favorite_user_rel', 'user_id', 'product_id')
