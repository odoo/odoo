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
from odoo import fields, models


class PatientRoom(models.Model):
    """Class holding Patient room details"""
    _name = 'patient.room'
    _description = 'Patient Room'

    name = fields.Char(string="Name", help='The name of room', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.user.company_id
                                  .currency_id.id,
                                  required=True, help='Currency in which '
                                                      'payments will be done')
    building_id = fields.Many2one('hospital.building',
                                  string="Block Name",
                                  required="True", help='Building to which '
                                                        'the room corresponds '
                                                        'to')
    nurse_ids = fields.Many2many('hr.employee', string='Nurses',
                                 domain="[('job_id.name','=','Nurse')]",
                                 help='Nurses of the room')
    bed_type = fields.Selection([('gatch', 'Gatch Bed'),
                                 ('electric', 'Electric'),
                                 ('stretcher', 'Stretcher'),
                                 ('low', 'Low Bed'),
                                 ('air', 'Low Air Loss'),
                                 ('circo', 'Circo Electric'),
                                 ('clinitron', 'Clinitron'),
                                 ], string="Bed Type", help='Select the type '
                                                            'of bed')
    rent = fields.Monetary(string='Rent', help='Rent for the room')
    state = fields.Selection([('avail', 'Available'),
                              ('reserve', 'Reserve'),
                              ('not', 'Unavailable'), ],
                             string='State', readonly=True,
                             default="avail", help='State of room')
    room_facilities_ids = fields.Many2many('room.facility',
                                           string='Facilities',
                                           help='Facilities of room')
    floor_no = fields.Integer(string="Floor No.", help='The floor to '
                                                       'which the room '
                                                       'corresponds to')

    _sql_constraints = [('unique_room', 'unique (name)',
                         'Room number should be unique!')]
