from odoo import fields, models
from odoo.addons import loyalty, point_of_sale


class ResPartner(loyalty.ResPartner, point_of_sale.ResPartner):

    loyalty_card_count = fields.Integer(groups='base.group_user,point_of_sale.group_pos_user')
