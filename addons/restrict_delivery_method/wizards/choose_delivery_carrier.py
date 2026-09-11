# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Shafna K(odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from odoo import fields, models


class ChooseDeliveryCarrier(models.TransientModel):
    """This class contains the fields in wizard which is related
    to that particular sale order"""
    _inherit = "choose.delivery.carrier"

    delivery_method_ids = fields.Many2many('delivery.carrier', related=
                                           'order_id.delivery_method_ids',
                                           help="Choose the delivery method")
    carrier_id = fields.Many2one('delivery.carrier', string="Shipping Method",
                                 help="Fill this field if you plan to invoice "
                                      "the shipping based on picking.",
                                 required=True)
