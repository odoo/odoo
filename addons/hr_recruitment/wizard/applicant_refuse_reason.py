# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ApplicantGetRefuseReason(models.TransientModel):
    _name = 'applicant.get.refuse.reason'
    _description = 'Get Refuse Reason'

    refuse_reason_id = fields.Many2one('hr.applicant.refuse.reason', 'Refuse Reason', required=True)
    applicant_ids = fields.Many2many('hr.applicant')
    send_mail = fields.Boolean("Send Email", compute='_compute_send_mail', store=True, readonly=False)
    template_id = fields.Many2one('mail.template', string='Email Template',
        compute='_compute_send_mail', store=True, readonly=False,
        domain="[('model', '=', 'hr.applicant')]")
    applicant_without_email = fields.Text(compute='_compute_applicant_without_email',
        string='Applicant(s) not having email')
    applicant_emails = fields.Text(compute='_compute_applicant_emails')

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
                    "\n".join([i.partner_name or i.name for i in applicants])
                )
            else:
                wizard.applicant_without_email = False

    @api.depends('applicant_ids.email_from')
    def _compute_applicant_emails(self):
        for wizard in self:
            wizard.applicant_emails = ', '.join(a.email_from for a in wizard.applicant_ids if a.email_from)

    def action_refuse_reason_apply(self):
        if self.send_mail:
            if not self.template_id:
                raise UserError(_("Email template must be selected to send a mail"))
            if not self.applicant_ids.filtered(lambda x: x.email_from or x.partner_id.email):
                raise UserError(_("Email of the applicant is not set, email won't be sent."))
        self.applicant_ids.write({'refuse_reason_id': self.refuse_reason_id.id, 'active': False})
        if self.send_mail:
            applicants = self.applicant_ids.filtered(lambda x: x.email_from or x.partner_id.email)
            # TDE note: keeping 16.0 behavior, clean me please
            message_values = {
                'email_layout_xmlid' : 'hr_recruitment.mail_notification_light_without_background',
            }
            if len(applicants) > 1:
                applicants.with_context(active_test=True).message_mail_with_source(
                    self.template_id,
                    auto_delete_keep_log=False,
                    **message_values
                )
            else:
                applicants.with_context(active_test=True).message_post_with_source(
                    self.template_id,
                    subtype_xmlid='mail.mt_note',
                    **message_values
                )
