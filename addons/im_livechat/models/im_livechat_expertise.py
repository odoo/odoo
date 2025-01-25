# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Im_LivechatExpertise(models.Model):
    """Expertise of Live Chat users."""

    _name = "im_livechat.expertise"
    _description = "Live Chat Expertise"
    _order = "name"

    name = fields.Char("Name", required=True, translate=True)
    user_ids = fields.Many2many("res.users", "im_livechat_expertise_res_users_rel", "expertise_id", "user_id", string="Operators")

    _name_unique = models.UniqueIndex("(name)")
