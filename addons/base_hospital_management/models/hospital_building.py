# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Techno Solutions  (odoo@cybrosys.com)
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
################################################################################
from odoo import api, fields, models


class HospitalBuilding(models.Model):
    """Class containing field and functions related to hospital building"""
    _name = 'hospital.building'
    _description = 'Buildings'

    notes = fields.Text(string='Notes', help='Notes regarding the building')
    name = fields.Char(string='Block Code',
                       help='Code for uniquely identifying a block',
                       copy=False, readonly=True, index=True,
                       default=lambda self: 'New')
    phone = fields.Char(string='Phone',
                        help='Phone number for contact the building')
    mobile = fields.Char(string='Mobile',
                         help='Mobile number for contact the building')
    email = fields.Char(string='Email', help='Email of the building')
    room_count = fields.Integer(string="Rooms",
                                help='Number of rooms in the building',
                                compute="_compute_room_count")
    ward_count = fields.Integer(string="Wards",
                                help='Number of wards in the building',
                                compute="_compute_ward_count")

    @api.model
    def create(self, vals):
        """Create building sequence"""
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'building.sequence') or 'New'
        return super().create(vals)

    def _compute_room_count(self):
        """Calculates room_count in a building"""
        for rec in self:
            rec.room_count = self.env['patient.room'].sudo().search_count([(
                'building_id', '=', rec.id)])

    def _compute_ward_count(self):
        """Counting wards in the building"""
        for rec in self:
            rec.ward_count = self.env['hospital.ward'].sudo().search_count([(
                'building_id', '=', rec.id)])

    def get_room_count(self):
        """Smart button action for viewing all rooms in a building"""
        return {
            'name': 'Room',
            'domain': [('building_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'res_model': 'patient.room',
            'view_mode': 'tree,form',
            'context': {'create': False},
        }

    def get_ward_count(self):
        """Smart button action for viewing all wards in a building"""
        return {
            'name': 'Wards',
            'domain': [('building_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'res_model': 'hospital.ward',
            'view_mode': 'tree,form',
            'context': {'create': False},
        }
