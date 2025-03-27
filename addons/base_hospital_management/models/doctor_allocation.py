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
from odoo.exceptions import ValidationError


class DoctorAllocation(models.Model):
    """Class holding doctor allocations"""
    _name = 'doctor.allocation'
    _description = 'Doctor Allocation'

    doctor_id = fields.Many2one('hr.employee', string="Doctor",
                                help='Name of the doctor',
                                domain=[('job_id.name', '=', 'Doctor')])
    name = fields.Char(string="Name", readonly=True, default='New',
                       help='Name of the allocation')
    department_id = fields.Many2one(string='Department',
                                    help='Department of the doctor',
                                    related='doctor_id.department_id')
    op_ids = fields.One2many('hospital.outpatient',
                             'doctor_id',
                             string='Booking',
                             help='Patient booking belongs to this '
                                  'allocation')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company.id,
                                 help='Indicates the company')
    is_doctor = fields.Boolean(string='Is Doctor', help='True for doctors.')
    date = fields.Date(string='Date',
                       help='Indicate the allocated date for a doctor',
                       default=fields.Date.today())
    work_to = fields.Float(string='Work To', required=True,
                           help='Allocation time ending time in 24 hrs format')
    work_from = fields.Float(string='Work From', required=True,
                             help='Allocation time starting time in 24 hrs '
                                  'format')
    time_avg = fields.Float(string='Duration', help="Average Consultation time "
                                                    "per Patient in minutes",
                            readonly=False,
                            related='doctor_id.time_avg')
    patient_type = fields.Selection([('inpatient', 'Inpatient'),
                                     ('outpatient', 'Outpatient')],
                                    string='Patient Type',
                                    help='Indicates the type of patient')
    patient_limit = fields.Integer(string='Limit Patient',
                                   help='Maximum number of patients allowed '
                                        'per allocation', store=True,
                                   compute='_compute_patient_limit', )
    patient_count = fields.Integer(string='Patient Count',
                                   help='Number of patient under '
                                        'this allocation',
                                   compute='_compute_patient_count')
    slot_remaining = fields.Integer(string='Slots Remaining',
                                    help='Number of slots remaining in this'
                                         ' allocation', store=True,
                                    compute='_compute_slot_remaining')
    latest_slot = fields.Float(string='Available Slot',
                               help='Indicates the latest available slot')
    state = fields.Selection(
        [('draft', 'Draft'), ('confirm', 'Confirmed'),
         ('cancel', 'Cancelled')],
        default='draft', string='State', help='State of Doctor allocation')

    @api.model
    def create(self, vals):
        """Method for creating name"""
        work_from_hr = int(vals['work_from'])
        work_from_min = int((vals['work_from'] - work_from_hr) * 60)
        work_from = "{:02d}:{:02d}".format(work_from_hr, work_from_min)
        work_to_hr = int(vals['work_to'])
        work_to_min = int((vals['work_to'] - work_to_hr) * 60)
        work_to = "{:02d}:{:02d}".format(work_to_hr, work_to_min)
        doctor_group = self.env.ref(
            'base_hospital_management.base_hospital_management_group_doctor')
        if doctor_group in self.env.user.groups_id:
            default_doctor_id = self.env['hr.employee'].sudo().search(
                [('user_id', '=', self.env.user.id)], limit=1)
            if default_doctor_id:
                vals[
                    'name'] = (default_doctor_id.name + ': ' + work_from + '-'
                               + work_to)
        else:
            vals['name'] = self.env['hr.employee'].sudo().browse(
                vals['doctor_id']).name + ': ' + work_from + '-' + work_to
        return super().create(vals)

    @api.onchange('work_from', 'work_to')
    def _onchange_work_from(self):
        """Method for calculating name"""
        if self.work_from and self.work_to:
            work_from_hr = int(self.work_from)
            work_from_min = int((self.work_from - work_from_hr) * 60)
            work_from = "{:02d}:{:02d}".format(work_from_hr, work_from_min)
            work_to_hr = int(self.work_to)
            work_to_min = int((self.work_to - work_to_hr) * 60)
            work_to = "{:02d}:{:02d}".format(work_to_hr, work_to_min)
            self.name = self.doctor_id.name + ': ' + work_from + '-' + work_to

    @api.model
    def default_get(self, doctor_id):
        """Method for making doctor field readonly and applying default value
        for doctor login"""
        res = super().default_get(doctor_id)
        doctor_group = self.env.ref(
            'base_hospital_management.base_hospital_management_group_doctor')
        if doctor_group in self.env.user.groups_id:
            default_doctor_id = self.env['hr.employee'].sudo().search(
                [('user_id', '=', self.env.user.id)], limit=1)
            if default_doctor_id:
                res['doctor_id'] = default_doctor_id.id
                res['is_doctor'] = True
                self.is_doctor = True
        else:
            self.is_doctor = False
            res['is_doctor'] = False
        return res

    @api.constrains('work_from', 'work_to', 'date')
    def _check_overlap(self):
        """Method for checking overlapping"""
        for allocation in self:
            if allocation.work_from >= allocation.work_to:
                raise ValidationError("Work From must be less than Work To.")
            overlapping_allocations = self.sudo().search([
                ('id', '!=', allocation.id),
                ('date', '=', allocation.date),
                ('doctor_id', '=', allocation.doctor_id.id),
                '|',
                '&', ('work_from', '<=', allocation.work_from),
                ('work_to', '>=', allocation.work_from),
                '&', ('work_from', '<=', allocation.work_to),
                ('work_to', '>=', allocation.work_to)
            ])
            if overlapping_allocations:
                raise ValidationError(
                    "Overlap detected with another doctor allocation on the "
                    "same date.")

    @api.depends('work_from', 'work_to', 'time_avg')
    def _compute_patient_limit(self):
        """Method for computing patient limit"""
        for record in self:
            if (record.work_from and record.work_to and record.time_avg
                    and record.time_avg > 0):
                patient_slots = int(
                    (record.work_to - record.work_from) / record.time_avg)
                if patient_slots <= 0:
                    raise ValidationError(
                        "Work From must be less than Work To.")
                else:
                    record.patient_limit = patient_slots
            else:
                record.patient_limit = 0

    @api.depends('op_ids')
    def _compute_patient_count(self):
        """Method for computing patient count"""
        for rec in self:
            rec.patient_count = len(rec.op_ids)

    @api.depends('op_ids', 'patient_count', 'patient_limit')
    def _compute_slot_remaining(self):
        """Method for computing slot remaining"""
        for rec in self:
            rec.slot_remaining = rec.patient_limit - rec.patient_count

    def action_get_patient_booking(self):
        """Returns form view of bed"""
        return {
            'name': "Patient Booking",
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'hospital.outpatient',
            'domain': [('id', 'in', self.op_ids.ids)],
            'context': {'create': False}
        }

    def action_confirm_allocation(self):
        """Confirmation of allocation"""
        self.state = 'confirm'

    def action_cancel_allocation(self):
        """Method for cancelling a allocation"""
        self.state = 'cancel'

    @api.model
    def get_allocation_lines(self):
        """Returns allocated hour details to display on the dashboard"""
        data_list = []
        allocated_hour = self.sudo().search([
            ('doctor_id.user_id', '=', self.env.user.id)
        ])
        for rec in allocated_hour:
            data_list.append({
                'date': rec.date,
                'name': rec.name,
                'patient_type': rec.patient_type,
                'patient_limit': rec.patient_limit,
                'patient_count': rec.patient_count
            })
        return {'record': data_list}
