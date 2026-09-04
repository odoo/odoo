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


class DoctorSlot(models.Model):
    """Model for handling a doctor's slot for surgery"""
    _name = 'doctor.slot'
    _description = "Doctor Slot"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    doctor_id = fields.Many2one('hr.employee', string="Doctor",
                                help='Doctors name',
                                domain=[('job_id.name', '=', 'Doctor')])
    date_start = fields.Datetime(default=fields.date.today(), string='Date',
                                 help='Date of surgery')
    patient_id = fields.Many2one('res.partner',
                                 domain=[('patient_seq', 'not in',
                                          ['New', 'Employee', 'User'])],
                                 string='Patient', help='Name of the patient')
    name = fields.Char(string='Surgery', help='Name of surgery')
    state = fields.Selection([('confirmed', 'Confirmed'),
                              ('cancel', 'Cancel'),
                              ('done', 'Done'),
                              ('draft', 'Draft')], default='draft',
                             string='State', help='State of the slot')
    time = fields.Float(string='Time', help='Time of surgery')
    hours_to_take = fields.Float(string='Duration',
                                 help='Time duration for the surgery')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company.id)

    def hospital_inpatient_confirm(self):
        """Inpatient confirmation from Doctor's dashboard"""
        data_list = []
        for rec in self.env['doctor.slot'].sudo().search(
                [('doctor_id.user_id', '=', self.env.user.id),
                 ('state', '=', 'confirmed')]):
            data_list.append({
                'id': rec.id,
                'planned_date': rec.date_start,
                'patient_id': rec.patient_id.name,
                'name': rec.name,
                'state': rec.state
            })
        return {
            'record': data_list
        }

    def hospital_inpatient_cancel(self):
        """Inpatients cancellation from Doctor's dashboard"""
        data_list = []
        for rec in self.env['doctor.slot'].sudo().search(
                [('doctor_id.user_id', '=', self.env.user.id),
                 ('state', '=', 'cancel')]):
            data_list.append({
                'id': rec.id,
                'planned_date': rec.date_start,
                'patient_id': rec.patient_id.name,
                'name': rec.name,
                'state': rec.state
            })
        return {
            'record': data_list
        }

    def hospital_inpatient_done(self):
        """Inpatient done function from doctor's dashboard"""
        data_list = []
        for rec in self.env['doctor.slot'].sudo().search(
                [('doctor_id.user_id', '=', self.env.user.id),
                 ('state', '=', 'done')]):
            data_list.append({
                'id': rec.id,
                'planned_date': rec.date_start,
                'patient_id': rec.patient_id.name,
                'name': rec.name,
                'state': rec.state
            })
        return {
            'record': data_list
        }

    def action_get_doctor_slot(self):
        """Function for returning doctor's slot to doctor's dashboard"""
        data_list = []
        for rec in self.sudo().search(
                [('doctor_id.user_id', '=', self.env.user.id),
                 ('state', '=', 'draft')]):
            data_list.append({
                'id': rec.id,
                'planned_date': rec.date_start,
                'patient_id': rec.patient_id.patient_seq,
                'name': rec.name,
                'state': rec.state
            })
        return {
            'record': data_list
        }

    def action_confirm(self):
        """Function for confirming a slot"""
        self.sudo().write({
            'state': 'confirmed'
        })

    def action_cancel(self):
        """Function for cancelling a slot"""
        self.sudo().write({
            'state': 'cancel'
        })

    def action_done(self):
        """Function for change the state to done"""
        self.sudo().write({
            'state': 'done'
        })
