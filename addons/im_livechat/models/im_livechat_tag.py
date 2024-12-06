# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Im_LivechatTag(models.Model):
    """ Tags of livechat users """
    _description = "Livechat Tags"
    _order = "name"

    name = fields.Char("Name", required=True, translate=True)

    _name_uniq = models.Constraint("unique (name)", "A tag with the same name already exists.")
