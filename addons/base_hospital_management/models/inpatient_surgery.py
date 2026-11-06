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


class InpatientSurgery(models.Model):
    """Class holding Surgery details"""
    _name = 'inpatient.surgery'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = 'Inpatient Surgery'

    date = fields.Date(dafault=fields.date.today(), string='Date',
                       help='Date of adding surgery')
    planned_date = fields.Datetime(string='Planned Date',
                                   help='Planned date for surgery',
                                   required=True)
    name = fields.Char(string='Name', help='Name of the surgery',
                       required=True)
    doctor_id = fields.Many2one('hr.employee',
                                string="Operating Doctor",
                                domain=[('job_id.name', '=', 'Doctor')],
                                help='Doctor responsible for the surgery',
                                required=True)
    inpatient_id = fields.Many2one('hospital.inpatient',
                                   string='Inpatient',
                                   help='Inpatient to whom surgery is added')
    hours_to_take = fields.Float(string='Duration',
                                 help='Time duration for the surgery')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company.id)
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed'),
                              ('done', 'Done'), ('cancel', 'Cancel'),
                              ], default='draft',
                             string='State', help='State of the slot')

    def action_confirm(self):
        """Function for confirming a surgery"""
        self.sudo().write({
            'state': 'confirmed'
        })

    def action_cancel(self):
        """Function for cancelling a surgery"""
        self.sudo().write({
            'state': 'cancel'
        })

    def action_done(self):
        """Function for change the state to surgery"""
        self.sudo().write({
            'state': 'done'
        })

    @api.model
    def get_doctor_slot(self):
        """Function for returning surgery details to doctor's dashboard"""
        data_list = []
        state = {'confirmed': 'Confirmed',
                 'cancel': 'Cancel',
                 'done': 'Done',
                 'draft': 'Draft'}
        for rec in self.sudo().search(
                [('doctor_id.user_id', '=', self.env.user.id)]):
            data_list.append({
                'id': rec.id,
                'planned_date': rec.planned_date,
                'patient_id': rec.inpatient_id.patient_id.name,
                'surgery_name': rec.name,
                'state': state[rec.state]
            })
        return {
            'record': data_list
        }
