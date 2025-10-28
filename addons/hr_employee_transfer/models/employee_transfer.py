# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class EmployeeTransfer(models.Model):
    """Model for managing employee transfers between companies."""
    _name = 'employee.transfer'
    _description = 'Employee Transfer'
    _order = "id desc"

    name = fields.Char(
        string='Name', help='Name of the Transfer',
        copy=False, default=lambda self: _('New'), readonly=True)
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True,
        help='Select the employee who is being transferred.')
    old_employee_id = fields.Many2one(
        'hr.employee', string='Old Employee')
    transfer_date = fields.Date(string='Date', default=fields.Date.today(),
                                help="Transfer date")
    transfer_company_id = fields.Many2one(
        'res.company', string='Transfer To',
        help="Select the company to which the employee is being transferred",
        copy=False, required=True)
    state = fields.Selection(
        [('draft', 'New'), ('transfer', 'Transferred'), ('cancel', 'Cancelled'),
         ('done', 'Done')],
        string='Status', readonly=True, copy=False, default='draft',
        help="""New: Transfer is created and not confirmed.
        Transferred: Transfer is confirmed. Transfer stays in this status till
         the transferred Branch receive the employee.
        Done: Employee is Joined/Received in the transferred Branch.
        Cancelled: Transfer is cancelled.""")
    company_id = fields.Many2one('res.company', string='Company',
                                 related='employee_id.company_id',
                                 help="The current company of the employee before the transfer.")
    note = fields.Text(
        string='Internal Notes',
        help="Enter any relevant notes regarding the transfer process or reasons for transfer.")
    transferred = fields.Boolean(
        string='Transferred', copy=False, help="Transferred",
        default=False, compute='_compute_transferred')
    responsible_employee_id = fields.Many2one(
        comodel_name='hr.employee', string='Responsible',
        default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1),
        readonly=True,
        help="The person responsible for the transfer.")

    def _compute_transferred(self):
        """Compute the 'transferred' status for the record."""
        for transfer in self:
            transfer.transferred = transfer.transfer_company_id in transfer.env.user.company_ids

    @api.model
    def create(self, vals_list):
        """Create an employee transfer record and prefix the 'name' with 'Transfer: ' followed by the employee's name."""
        for vals in vals_list:
            employee_id = vals.get('employee_id')
            employee = self.env['hr.employee'].browse(employee_id)
            vals['name'] = "Transfer: " + employee.name
        return super(EmployeeTransfer, self).create(vals_list)

    def action_transfer(self):
        """Handle employee transfer logic."""
        if not self.transfer_company_id:
            raise UserError(_('Please select a company for the transfer.'))
        if self.transfer_company_id == self.company_id:
            raise UserError(_('You cannot transfer the employee to the same company.'))
        self.state = 'transfer'

    def action_receive_employee(self):
        """Handle employee reception logic during the transfer."""
        employee_data = self.employee_id.sudo().read(
            ['name', 'image_1920','private_email', 'sex', 'identification_id', 'passport_id', 'birthday', 'legal_name',
             'place_of_birth', 'emergency_contact', 'emergency_phone', 'country_id'])[0]
        del employee_data['id']
        employee_data.update({
            'company_id': self.transfer_company_id.id
        })
        new_employee = self.env['hr.employee'].sudo().create(employee_data)

        # Set the contract start date for the new employee
        new_employee.contract_date_start = self.transfer_date
        self.old_employee_id = self.employee_id
        self.employee_id = new_employee
        self.old_employee_id.sudo().active = False
        self.state = 'done'

        return {
            'name': _('Employees'),
            'view_mode': 'form',
            'res_model': 'hr.employee',
            'res_id': new_employee.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    def cancel_transfer(self):
        """Transfer cancel function."""
        self.state = 'cancel'
