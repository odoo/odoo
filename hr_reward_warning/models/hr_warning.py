# -*- coding: utf-8 -*-
###################################################################################
#    A part of OpenHRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2018-TODAY Cybrosys Technologies (<https://www.cybrosys.com>).
#    Author: Jesni Banu (<https://www.cybrosys.com>)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###################################################################################
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrAnnouncementTable(models.Model):
    _name = 'hr.announcement'
    _description = 'HR Announcement'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Code No:', help="Sequence Number of the Announcement")
    announcement_reason = fields.Text(string='Title', states={'draft': [('readonly', False)]}, required=True,
                                      readonly=True, help="Announcement Subject")
    state = fields.Selection([('draft', 'Draft'), ('to_approve', 'Waiting For Approval'),
                              ('approved', 'Approved'), ('rejected', 'Refused'), ('expired', 'Expired')],
                             string='Status',  default='draft',
                             track_visibility='always')
    requested_date = fields.Date(string='Requested Date', default=datetime.now().strftime('%Y-%m-%d'),
                                 help="Create Date of Record")
    attachment_id = fields.Many2many('ir.attachment', 'doc_warning_rel', 'doc_id', 'attach_id4',
                                     string="Attachment", help='You can attach the copy of your Letter')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.user.company_id, readonly=True, help="Login user Company")
    is_announcement = fields.Boolean(string='Is general Announcement?', help="To set Announcement as general announcement")
    announcement_type = fields.Selection([('employee', 'By Employee'), ('department', 'By Department'), ('job_position', 'By Job Position')])
    employee_ids = fields.Many2many('hr.employee', 'hr_employee_announcements', 'announcement', 'employee',
                                    string='Employees', help="Employee's which want to see this announcement")
    department_ids = fields.Many2many('hr.department', 'hr_department_announcements', 'announcement', 'department',
                                      string='Departments', help="Department's which want to see this announcement")
    position_ids = fields.Many2many('hr.job', 'hr_job_position_announcements', 'announcement', 'job_position',
                                    string='Job Positions',help="Job Position's which want to see this announcement")
    announcement = fields.Html(string='Letter', states={'draft': [('readonly', False)]}, readonly=True, help="Announcement Content")
    date_start = fields.Date(string='Start Date', default=fields.Date.today(), required=True, help="Start date of "
                                                                                                   "announcement want"
                                                                                                   " to see")
    date_end = fields.Date(string='End Date', default=fields.Date.today(), required=True, help="End date of "
                                                                                               "announcement want too"
                                                                                               " see")

    def reject(self):
        self.state = 'rejected'

    def approve(self):
        self.state = 'approved'

    def sent(self):
        self.state = 'to_approve'

    @api.constrains('date_start', 'date_end')
    def validation(self):
        if self.date_start > self.date_end:
            raise ValidationError("Start date must be less than End Date")

    @api.model
    def create(self, vals):
        if vals.get('is_announcement'):
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.announcement.general')
        else:
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.announcement')
        return super(HrAnnouncementTable, self).create(vals)

    def get_expiry_state(self):
        """
        Function is used for Expiring Announcement based on expiry date
        it activate from the crone job.

        """
        now = datetime.now()
        now_date = now.date()
        ann_obj = self.search([('state', '!=', 'rejected')])
        for recd in ann_obj:
            if recd.date_end < now_date:
                recd.write({
                    'state': 'expired'
                })
