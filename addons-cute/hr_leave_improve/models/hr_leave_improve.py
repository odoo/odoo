# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.translate import _
import base64


class HolidaysRequest(models.Model):
    _inherit = "hr.leave"

    leave_reason = fields.Selection([('yillik', 'Yıllık İzin'), ('mazeret', 'Mazeret İzni')], string='İzin Sebebi', default='yillik')

    def action_send_email(self):
        print(self)

        template = self.env.ref('auth_signup.reset_password_email')
        email_values = {
            'email_cc': False,
            'auto_delete': True,
            'recipient_ids': [],
            'partner_ids': [],
            'scheduled_date': False,
        }

        resUser = self.env['res.users'].browse(2)

        for usr in resUser:
            if not usr.email:
                raise UserError(_("Cannot send email: user %s has no email address.", usr.name))
            email_values['email_to'] = usr.email

        template.send_mail(usr.id, force_send=True, raise_exception=True, email_values=email_values)

        raise UserError(_('Time off request state must be "Refused" or "To Approve" in order to be reset to draft.'))
        return True

    def send_email_with_pdf_attach(self):
        repdata = self.env.ref('hr_leave_improve.hr_leave_improve_report')

        report = repdata._render_qweb_pdf([self.id], data={'report_type': 'pdf'})

        data_record = base64.b64encode(report[0])

        ir_values = {
            'name': 'Izin Formu',
            'type': 'binary',
            'datas': data_record,
            'store_fname': data_record,
            'mimetype': 'application/pdf',
            'res_model': 'hr.leave',
        }

        report_attachment = self.env['ir.attachment'].create(ir_values)

        email_template = self.env.ref('hr_leave_improve.hr_leave_improve_belsis_mail_template')

        email_template.attachment_ids = [report_attachment.id]

        email_template.send_mail(self.id)

        email_template.attachment_ids = []
