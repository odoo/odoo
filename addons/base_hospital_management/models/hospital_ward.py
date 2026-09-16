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


class HospitalWard(models.Model):
    """Class holding Ward details"""
    _name = 'hospital.ward'
    _description = 'Hospital Ward'
    _rec_name = 'ward_no'

    ward_no = fields.Char(string="Name",
                          required="True", help='Number of the ward')
    building_id = fields.Many2one('hospital.building',
                                  string="Block", help='The building to '
                                                       'which the ward '
                                                       'corresponds to')
    floor_no = fields.Integer(string="Floor No.", help='The floor to '
                                                       'which the ward '
                                                       'corresponds to')
    note = fields.Text(string="Note", help='Note regarding the ward')
    bed_count = fields.Integer(string="Count", compute="_compute_bed_count",
                               help='The bed count')
    nurse_ids = fields.Many2many('hr.employee', string='Nurses',
                                 domain="[('job_id','=','Nurse')]",
                                 help='Nurses corresponds to the ward')
    ward_facilities_ids = fields.Many2many('room.facility',
                                           string='Facilities',
                                           help='Facilities corresponds to '
                                                'ward.')
    _sql_constraints = [('unique_ward', 'unique (ward_no)',
                         'Ward number should be unique!')]

    def _compute_bed_count(self):
        """Method for computing bed count"""
        for rec in self:
            rec.bed_count = rec.env['hospital.bed'].sudo().search_count([(
                'ward_id', '=', rec.ward_no)])

    @api.onchange('building_id')
    def _onchange_building_id(self):
        """Returns domain for the field bed_id"""
        return {'domain': {
            'bed_id': [
                ('ward_id', '=', self.id),
            ]}}

    def action_get_open_bed(self):
        """Returns form view of bed"""
        return {
            'name': 'Bed',
            'domain': [('ward_id', '=', self.ward_no)],
            'type': 'ir.actions.act_window',
            'res_model': 'hospital.bed',
            'view_mode': 'tree',
            'context': {'create': False},
        }
