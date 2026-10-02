# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Techno Solutions (odoo@cybrosys.com)
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
#############################################################################
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """
    Inherits the Res Config Settings model to add two many-to-one fields for
    selecting source and destination locations. These fields are used to
    configure the source and destination locations for stock reservations.
    """
    _inherit = 'res.config.settings'

    source_location_id = fields.Many2one(
        "stock.location",
        String="Source Location",
        config_parameter='sales_stock_reservation.source_location_id',
        help='This is a Many2one field that refers to the location from '
             'which the products will be sourced.')
    destination_location_id = fields.Many2one(
        "stock.location",
        String="Destination Location",
        config_parameter='sales_stock_reservation.destination_location_id',
        help='This is a Many2one field that refers to the location to which '
             'the products will be delivered.')
