# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Sahla Sherin (<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models


class ResPartner(models.Model):
    """Inherited the partner model for adding gym related fields."""
    _inherit = 'res.partner'

    gym_member = fields.Boolean(string='Gym Member', default=True,
                                help='This field define the whether is member'
                                     'of gym')
    membership_count = fields.Integer('membership_count',
                                      compute='_compute_membership_count',
                                      help='This help to count the membership')
    measurement_count = fields.Integer('measurement_count',
                                       compute='_compute_measurement_count',
                                       help='This helps to get the umber of '
                                            'measurements for gym members')

    def _compute_membership_count(self):
        """Number of membership for gym members """
        for rec in self:
            rec.membership_count = self.env['gym.membership'].search_count([
                ('member_id', '=', rec.id)])

    def _compute_measurement_count(self):
        """Number of measurements for gym members """
        for rec in self:
            rec.measurement_count = self.env[
                'measurement.history'].search_count([('member_id', '=',
                                                      rec.id)])

    @api.constrains('gym_member')
    def _validate_gym_member(self):
        """Select sale person to assign workout plan """
        if self.gym_member:
            return {
                'warning': {
                    'title': 'User Error',
                    'message': 'select sale person (sales & purchase) '
                               'to assign workout plan'}
            }
