# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, models


class StockPicking(models.Model):
    """Extends stock picking to apply domain restrictions based on user's
    assigned warehouses."""
    _inherit = 'stock.picking'

    @api.onchange('location_id', 'location_dest_id')
    def _onchange_location_id(self):
        """Domain for location_id and location_dest_id."""
        if self.env['ir.config_parameter'].sudo().get_param('user_warehouse_restriction.group_user_warehouse_restriction'):
            return {
            'domain': {'location_id': [
                ('warehouse_id.user_ids', 'in', self.env.user.id)],
                'location_dest_id': [
                    ('warehouse_id.user_ids', 'in', self.env.user.id)]}}


