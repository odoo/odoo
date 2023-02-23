# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class PosOrder(models.Model):
    _inherit = 'pos.order'
    # When the order is set to not trusted, a warning message will appear POS app.
    # The server will have a button to acknowledge the order.
    # we make the order trusted by default;
    # we set it as not trusted from the controller of the pos_self_order module
    is_trusted =  fields.Boolean(
        string='Order is trusted', default='True', 
        help="An order created by a logged in user is trusted. An order created by a public user using the self order app is only trusted after a user of the POS app acknowledges it."
        )
