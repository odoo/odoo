# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2021-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: odoo@cybrosys.com
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
#############################################################################

import datetime
from odoo import models, fields, api, _


class VisitDetails(models.Model):
    _name = 'fo.visit'
    _inherit = ['mail.thread']
    _description = 'Visit'

    name = fields.Char(string="sequence", default=lambda self: _('New'))
    visitor = fields.Many2one("fo.visitor", string='Visitor')
    phone = fields.Char(string="Phone", required=True)
    email = fields.Char(string="Email", required=True)
    reason = fields.Many2many('fo.purpose', string='Purpose Of Visit',
                              required=True,
                              help='Enter the reason for visit')
    visitor_belongings = fields.One2many('fo.belongings',
                                         'belongings_id_fov_visitor',
                                         string="Personal Belongings",
                                         help='Add the belongings details '
                                              'here.')
    check_in_date = fields.Datetime(string="Check In Time",
                                    help='Visitor check in time automatically'
                                    ' fills when he checked in to the office.')
    check_out_date = fields.Datetime(string="Check Out Time",
                                     help='Visitor check out time'
                                          ' automatically fills when he '
                                          'checked out from the office.')
    visiting_person = fields.Many2one('hr.employee', string="Meeting With")
    department = fields.Many2one('hr.department', string="Department")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('check_in', 'Checked In'),
        ('check_out', 'Checked Out'),
        ('cancel', 'Cancelled'),
    ], tracking=True, default='draft')

    @api.model
    def create(self, vals):
        if vals:
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'fo.visit') or _('New')
            result = super(VisitDetails, self).create(vals)
            return result

    def action_cancel(self):
        self.state = "cancel"

    def action_check_in(self):
        self.state = "check_in"
        self.check_in_date = datetime.datetime.now()

    def action_check_out(self):
        self.state = "check_out"
        self.check_out_date = datetime.datetime.now()

    @api.onchange('visitor')
    def visitor_details(self):
        if self.visitor:
            if self.visitor.phone:
                self.phone = self.visitor.phone
            if self.visitor.email:
                self.email = self.visitor.email

    @api.onchange('visiting_person')
    def get_employee_dpt(self):
        if self.visiting_person:
            self.department = self.visiting_person.department_id


class PersonalBelongings(models.Model):
    _name = 'fo.belongings'
    _description = 'Personal Belongings'

    property_name = fields.Char(string="Property",
                                help='Employee belongings name')
    property_count = fields.Char(string="Count", help='Count of property')
    number = fields.Integer(compute='get_number', store=True, string="Sl")
    belongings_id_fov_visitor = fields.Many2one('fo.visit',
                                                string="Belongings")
    belongings_id_fov_employee = fields.Many2one('fo.property.counter',
                                                 string="Belongings")
    permission = fields.Selection([
        ('0', 'Allowed'),
        ('1', 'Not Allowed'),
        ('2', 'Allowed With Permission'),
        ], 'Permission', required=True, index=True, default='0', tracking=True)

    @api.depends('belongings_id_fov_visitor', 'belongings_id_fov_employee')
    def get_number(self):
        for visit in self.mapped('belongings_id_fov_visitor'):
            number = 1
            for line in visit.visitor_belongings:
                line.number = number
                number += 1
        for visit in self.mapped('belongings_id_fov_employee'):
            number = 1
            for line in visit.visitor_belongings:
                line.number = number
                number += 1


class VisitPurpose(models.Model):
    _name = 'fo.purpose'
    _description = 'Visit Purpose'

    name = fields.Char(string='Purpose', required=True,
                       help='Meeting purpose in short term.eg:Meeting.')
    description = fields.Text(string='Description Of Purpose',
                              help='Description for the Purpose.')
