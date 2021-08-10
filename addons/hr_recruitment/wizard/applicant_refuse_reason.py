# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ApplicantGetRefuseReason(models.TransientModel):
    _name = 'applicant.get.refuse.reason'
    _description = 'Get Refuse Reason'

    refuse_reason_id = fields.Many2one('hr.applicant.refuse.reason', 'Refuse Reason')
    applicant_ids = fields.Many2many('hr.applicant')
    send_mail = fields.Boolean("Send Email", compute='_compute_send_mail', store=True, readonly=False)
    template_id = fields.Many2one('mail.template', string='Email Template',
        compute='_compute_send_mail', store=True, readonly=False,
        domain="[('model', '=', 'hr.applicant')]")
    applicant_without_email = fields.Text(compute='_compute_applicant_without_email',
        string='Applicant(s) not having email')

    @api.depends('refuse_reason_id')
    def _compute_send_mail(self):
        for wizard in self:
            template = wizard.refuse_reason_id.template_id
            wizard.send_mail = bool(template)
            wizard.template_id = template

    @api.depends('applicant_ids', 'send_mail')
    def _compute_applicant_without_email(self):
        for wizard in self:
            applicants = wizard.applicant_ids.filtered(lambda x: not x.email_from and not x.partner_id.email)
            if applicants and wizard.send_mail:
                wizard.applicant_without_email = "%s\n%s" % (
                    _("The email will not be sent to the following applicant(s) as they don't have email address."),
                    "\n".join([i.partner_name for i in applicants])
                )
            else:
                wizard.applicant_without_email = False

    def action_refuse_reason_apply(self):
        if self.send_mail:
            if not self.template_id:
                raise UserError(_("Email template must be selected to send a mail"))
            if not self.applicant_ids.filtered(lambda x: x.email_from or x.partner_id.email):
                raise UserError(_("Email of the applicant is not set, email won't be sent."))
        self.applicant_ids.write({'refuse_reason_id': self.refuse_reason_id.id, 'active': False})
        if self.send_mail:
            applicants = self.applicant_ids.filtered(lambda x: x.email_from or x.partner_id.email)
            applicants.message_post_with_template(self.template_id.id, **{
                'auto_delete_message': True,
                'subtype_id': self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
                'email_layout_xmlid': 'mail.mail_notification_light'
            })
