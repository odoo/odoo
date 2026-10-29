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
from odoo import fields, models, _
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    """Inherited to add more fields and functions"""
    _inherit = 'hr.employee'

    doctor = fields.Boolean(string='Doctor', help='True for Doctors')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  help='Currency in which consultation fee '
                                       'is calculating',
                                  default=lambda self: self.env.user.company_id
                                  .currency_id.id,
                                  required=True)
    coach_id = fields.Many2one('hr.employee', string='Coach',
                               help='Name of the coach')
    consultancy_charge = fields.Monetary(string="Consultation Charge",
                                         help='Charge for consultation')
    consultancy_type = fields.Selection([('resident', 'Residential'),
                                         ('special', 'Specialist')],
                                        string="Consultation Type",
                                        help='Select the type of Consultation')
    time_avg = fields.Float(string='Average Time for a Patient',
                            help="Average Consultation time "
                                 "per Patient in minutes")
    degree_ids = fields.Many2many('hospital.degree',
                                  string="Degree",
                                  help='Degrees of staff')
    pharmacy_id = fields.Many2one('hospital.pharmacy',
                                  string="Pharmacy",
                                  help='Name of the pharmacy')
    specialization_ids = fields.Many2many('doctor.specialization',
                                          string="Specialization",
                                          help="Doctors specialization for"
                                               " an area")

    def action_create_user(self):
        """Updating employee field of res user to true"""
        self.ensure_one()
        if self.user_id:
            raise ValidationError(_("This employee already has an user."))
        return {
            'name': _('Create User'),
            'type': 'ir.actions.act_window',
            'res_model': 'res.users',
            'view_mode': 'form',
            'view_id': self.env.ref('hr.view_users_simple_form').id,
            'target': 'new',
            'context': {
                'default_create_employee_id': self.id,
                'default_name': self.name,
                'default_phone': self.work_phone,
                'default_mobile': self.mobile_phone,
                'default_login': self.work_email,
                'default_employee': True
            }
        }

    def _inverse_work_contact_details(self):
        """Override to prevent creating patient while creating a staff"""
        for employee in self:
            if not employee.work_contact_id:
                employee.work_contact_id = self.env[
                    'res.partner'].sudo().create(
                    {
                        'email': employee.work_email,
                        'mobile': employee.mobile_phone,
                        'name': employee.name,
                        'image_1920': employee.image_1920,
                        'company_id': employee.company_id.id,
                        'patient_seq': 'Employee'
                    })
            else:
                employee.work_contact_id.sudo().write({
                    'email': employee.work_email,
                    'mobile': employee.mobile_phone,
                    'patient_seq': 'Employee'
                })
