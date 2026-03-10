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
from datetime import date, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrEmployeeDocument(models.Model):
    """This class represents HR employee documents and provides methods
    for managing document expiry notifications."""
    _name = 'hr.employee.document'
    _description = 'HR Employee Documents'

    name = fields.Char(string='Document Number', required=True, copy=False,
                       help='You can give your Document number.')
    description = fields.Text(string='Description', copy=False,
                              help="Description of the documents.")
    expiry_date = fields.Date(string='Expiry Date', copy=False,
                              help="Expiry date of the documents.")
    employee_ref_id = fields.Many2one('hr.employee', invisible=1,
                                      copy=False,
                                      help='Specify the employee name.')
    doc_attachment_ids = fields.Many2many('ir.attachment',
                                          'doc_attach_rel',
                                          'doc_id', 'attach_id3',
                                          string="Attachment",
                                          help='You can attach the copy of your'
                                               ' document', copy=False)
    issue_date = fields.Date(string='Issue Date', default=fields.Date.today(),
                             help="Date of issued", copy=False)
    document_type_id = fields.Many2one('document.type',
                                       string="Document Type",
                                       help="Type of the document.")
    before_days = fields.Integer(string="Days",
                                 help="How many number of days before to get "
                                      "the notification email.")
    notification_type = fields.Selection([
        ('single', 'Notification on expiry date'),
        ('multi', 'Notification before few days'),
        ('everyday', 'Everyday till expiry date'),
        ('everyday_after', 'Notification on and after expiry')
    ], string='Notification Type',
        help="Select type of the documents expiry notification.")

    def mail_reminder(self):
        """Sending document expiry notification to employees."""
        for record in self.search([('expiry_date', '!=', False)]):
            exp_date = fields.Date.from_string(record.expiry_date)
            days_before = timedelta(days=record.before_days or 0)
            is_expiry_today = fields.Date.today() == exp_date
            is_notification_day = any([record.notification_type == 'single'
                                       and is_expiry_today,
                                       record.notification_type == 'multi'
                                       and (fields.Date.today() == fields.Date.
                                            from_string(
                                           record.expiry_date) - days_before
                                            or is_expiry_today),
                                       record.notification_type == 'everyday'
                                       and fields.Date.today() >= fields.Date.
                                      from_string(
                                           record.expiry_date) - days_before,
                                       record.notification_type ==
                                       'everyday_after'
                                       and fields.Date.today() <=
                                       fields.Date.from_string(
                                           record.expiry_date) + days_before,
                                       not record.notification_type and
                                       fields.Date.today() == fields.Date.
                                      from_string(
                                           record.expiry_date) - timedelta(
                                           days=7), ])
            if is_notification_day:
                employee_name = record.employee_ref_id.name
                document_name = record.name
                expiry_date_str = str(record.expiry_date)
                mail_content = (
                    f"Hello {employee_name},<br>Your Document {document_name} "
                    f"is going to expire on {expiry_date_str}. "
                    "Please renew it before the expiry date."
                )
                subject = _('Document-%s Expired On %s') % (
                    document_name, expiry_date_str)
                main_content = {
                    'subject': subject,
                    'author_id': self.env.user.partner_id.id,
                    'body_html': mail_content,
                    'email_to': record.employee_ref_id.work_email,
                }
                self.env['mail.mail'].create(main_content).send()

    @api.constrains('expiry_date')
    def _check_expiry_date(self):
        """This method is called as a constraint whenever the 'expiry_date'
         field of an 'hr.employee.document' record is modified."""
        for rec in self:
            if rec.expiry_date:
                exp_date = fields.Date.from_string(rec.expiry_date)
                if exp_date < date.today():
                    raise UserError(_('Your Document Is Expired.'))
