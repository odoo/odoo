# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
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
################################################################################
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LabTestLine(models.Model):
    """Class holing lab test line details"""
    _name = "lab.test.line"
    _description = "Lab Test Line"

    name = fields.Char(string='Test Sequence', required=True,
                       copy=False, readonly=True, index=True,
                       default=lambda self: 'New', help='Name of lab test line')
    patient_id = fields.Many2one('res.partner', string='Patient',
                                 help='Choose the patient',
                                 domain=[('patient_seq', 'not in',
                                          ['New', 'Employee', 'User'])])
    doctor_id = fields.Many2one('hr.employee', string='Doctor',
                                help='Choose the doctor',
                                domain=[('job_id.name', '=', 'Doctor')])
    date = fields.Date(default=fields.Date.today(), string='Date',
                       help='Date of test')
    test_ids = fields.Many2many('lab.test', string='Test',
                                help='All the tests')
    patient_type = fields.Selection(selection=[
        ('inpatient', 'Inpatient'), ('outpatient', 'Outpatient')
    ], required=1, string='Patient Type', help='Choose the patient type')
    op_id = fields.Many2one('hospital.outpatient', string='OP Number',
                            help='ID of outpatient')
    ip_id = fields.Many2one('hospital.inpatient', string='Inpatient ID',
                            help='ID of inpatient')
    state = fields.Selection(selection=[
        ('draft', 'Draft'), ('created', 'created')
    ], default='draft', string='State', help='State of the record')

    @api.model
    def create(self, vals):
        """Sequence generation"""
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'lab_tests.draft.sequence') or 'New'
        return super().create(vals)

    def action_confirm(self):
        """Method for confirming the test"""
        if not self.test_ids:
            raise UserError(_('You need to add a test before posting.'))
        self.state = 'created'
        self.env['patient.lab.test'].sudo().create({
            'patient_id': self.patient_id.id,
            'test_id': self.id,
            'patient_type': self.patient_type,
            'state': 'draft',
            'test_ids': self.test_ids.ids,
        })

    @api.model
    def action_get_patient_data(self, rec_id):
        """Method for fetching patient data"""
        data = self.env['lab.test.line'].sudo().browse(rec_id)
        if data:
            patient_data = {
                'id': rec_id,
                'name': data.patient_id.name,
                'unique': data.patient_id.patient_seq,
                'email': data.patient_id.email,
                'phone': data.patient_id.phone,
                'dob': data.patient_id.date_of_birth,
                'image_1920': data.patient_id.image_1920,
                'gender': data.patient_id.gender,
                'status': data.patient_id.marital_status,
                'doctor': data.doctor_id.name,
                'patient_type': data.patient_type.capitalize(),
                'ticket': data.op_id.op_reference
                if data.patient_type == 'outpatient' else data.ip_id.name,
                'test_data': []
            }
            if data.patient_id.blood_group:
                blood_caps = data.patient_id.blood_group.capitalize()
                patient_data['blood_group'] = blood_caps + str(
                    data.patient_id.rh_type),
            for test in data.test_ids:
                hours = int(test.patient_lead)
                minutes = int((test.patient_lead - hours) * 60)
                patient_data['test_data'].append({
                    'id': test.id,
                    'name': test.name,
                    'patient_lead': "{:02d}:{:02d}".format(hours, minutes),
                    'price': test.price,
                })
            return patient_data

    @api.model
    def create_lab_tests(self, data):
        """Method for creating lab tests"""
        test_ids = []
        test = self.env['lab.test.line'].sudo().browse(data['id'])
        test.state = 'created'
        if data:
            for rec in data['test_data']:
                test_ids.append(rec['id'])
        self.env['patient.lab.test'].sudo().create({
            'patient_id': test.patient_id.id,
            'test_id': data['id'],
            'patient_type': data['patient_type'].lower(),
            'state': 'draft',
            'test_ids': test_ids,
        })
        return {
            'message': 'success',
        }
