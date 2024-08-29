from odoo import fields, models
from odoo.addons import base


class ResPartner(models.Model, base.ResPartner):

    loyalty_card_count = fields.Integer(groups='base.group_user,point_of_sale.group_pos_user')
