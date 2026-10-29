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


class DoctorRound(models.Model):
    """Class holding doctor round details"""
    _name = 'doctor.round'
    _description = "Doctor Rounds"

    admission_id = fields.Many2one('hospital.inpatient',
                                   string='Patient',
                                   help='Choose the patient')
    doctor_id = fields.Many2one('hr.employee',
                                domain=[('job_id.name', '=', 'Doctor')],
                                string='Doctor', help='Choose your doctor')
    date = fields.Datetime(string='Visit Time', help='Choose the visit time '
                                                     'of doctor')
    status = fields.Char(string='Status', help='Status of doctor rounds')
    notes = fields.Text(string='Note', help='Notes regarding the rounds')
