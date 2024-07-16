# -*- coding: utf-8 -*-

from datetime import datetime
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression


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
    duplicates = fields.Boolean('Duplicates')
    duplicates_count = fields.Integer('Duplicates Count', compute='_compute_duplicates_count')

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

        refused_applications = self.applicant_ids
        if self.duplicates_count and self.duplicates:
            duplicate_domain = self.applicant_ids._get_similar_applicants_domain()
            duplicate_domain = expression.AND([duplicate_domain, [('application_status', '!=', 'refused')]])
            duplicates_ids = self.env['hr.applicant'].search(duplicate_domain)
            refused_applications |= duplicates_ids
            refuse_bodies = {}
            for duplicate in duplicates_ids:
                url = '/odoo/hr.applicant/%s' % (self.applicant_ids[0].id)
                message = _(
                    "Refused automatically because this application has been identified as a duplicate of %(link)s",
                    link=Markup("<a href=%s>%s</a>") % (url, self.applicant_ids[0].name))
                refuse_bodies[duplicate.id] = message

            duplicates_ids._message_log_batch(refuse_bodies)
        refused_applications.write({'refuse_reason_id': self.refuse_reason_id.id, 'active': False, 'refuse_date': datetime.now()})

        if self.send_mail:
            applicants = self.applicant_ids.filtered(lambda x: x.email_from or x.partner_id.email)
            # TDE note: keeping 16.0 behavior, clean me please
            message_values = {
                'email_layout_xmlid' : 'hr_recruitment.mail_notification_light_without_background',
            }
            if len(applicants) > 1:
                applicants.with_context(active_test=True).message_mail_with_source(
                    self.template_id,
                    auto_delete_keep_log=True,
                    **message_values
                )
            else:
                applicants.with_context(active_test=True).message_post_with_source(
                    self.template_id,
                    subtype_xmlid='mail.mt_note',
                    **message_values
                )

    @api.depends('applicant_ids')
    def _compute_duplicates_count(self):
        self.duplicates_count = self.applicant_ids.other_applications_count if len(self.applicant_ids) == 1 else 0
