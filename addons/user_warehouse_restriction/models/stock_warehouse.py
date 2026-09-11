# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Anagha S (odoo@cybrosys.com)
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
from odoo import api, fields, models


class StockWarehouse(models.Model):
    """Extends the 'stock.warehouse' model to add functionality for restricting
     stock location access to specific users within the system."""
    _inherit = "stock.warehouse"

    user_ids = fields.Many2many(
        comodel_name='res.users', string='Allowed Users',
        domain=lambda self: [
            ('groups_id', 'in', self.env.ref('stock.group_stock_user').id)],
        default=lambda self: self.env.user,
        help='Allowed users to this Warehouse.')
    restrict_location = fields.Boolean(
        string='Restrict Stock Location for this Warehouse',
        help='Restrict stock location of this warehouse to the selected '
             'users.')

    @api.onchange('restrict_location', 'user_ids')
    def _onchange_restrict_location(self):
        """Triggered when the 'restrict_location' or 'user_ids' fields
        are modified. It updates the 'restrict_location' field for selected
        users when restricting stock location access."""
        for rec in self.user_ids:
            if self.restrict_location:
                rec._origin.write({'restrict_location': True,
                                   'allowed_warehouse_ids': [
                                       (4, self._origin.id)]})
            elif not self.restrict_location:
                rec._origin.write({'restrict_location': True,
                                   'location_ids': False
                                   })

    def action_open_users_view(self):
        """Return user basic form view to give restricted location for users"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Users',
            'view_mode': 'tree,form',
            'res_model': 'res.users',
            'domain': [('id', 'in', [user.id for user in self.user_ids]),
                       ('groups_id', 'not in',
                        [self.env.ref('base.group_system').id])]}
