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
    single_applicant_email = fields.Char(compute='_compute_single_applicant_email', inverse="_inverse_single_applicant_email")

    @api.depends('refuse_reason_id')
    def _compute_send_mail(self):
        for wizard in self:
            template = wizard.refuse_reason_id.template_id
            wizard.send_mail = template and not wizard.applicant_without_email
            wizard.template_id = template

    @api.depends('applicant_ids', 'single_applicant_email')
    def _compute_applicant_without_email(self):
        for wizard in self:
            applicants = wizard.applicant_ids.filtered(lambda x: not x.email_from and not x.partner_id.email)
            if applicants and not wizard.single_applicant_email:
                wizard.applicant_without_email = "%s\n%s" % (
                    _("You can't select Send email option.\nThe email will not be sent to the following applicant(s) as they don't have an email address:"),
                    ",\n".join([i.partner_name or i.display_name for i in applicants])
                )
            else:
                wizard.applicant_without_email = False

    @api.depends("applicant_ids.email_from")
    def _compute_single_applicant_email(self):
        for wizard in self:
            if len(wizard.applicant_ids) == 1:
                wizard.single_applicant_email = (
                    wizard.applicant_ids.email_from
                    or wizard.applicant_ids.partner_id.email
                )

    def _inverse_single_applicant_email(self):
        for wizard in self:
            if len(wizard.applicant_ids) == 1:
                wizard.applicant_ids.email_from = wizard.single_applicant_email

    @api.depends('applicant_ids.email_from')
    def _compute_applicant_emails(self):
        for wizard in self:
            wizard.applicant_emails = ', '.join(a.email_from or a.partner_id.email for a in wizard.applicant_ids if a.email_from or a.partner_id.email)

    def action_refuse_reason_apply(self):
        if self.send_mail:
            if not self.template_id:
                raise UserError(_("Email template must be selected to send a mail"))
            if any(not (applicant.email_from or applicant.partner_id.email) for applicant in self.applicant_ids):
                raise UserError(_("At least one applicant doesn't have a email; you can't use send email option."))

        refused_applications = self.applicant_ids
        # duplicates_count can be true only if only one application is selected
        if self.duplicates_count and self.duplicates:
            applicant_id = self.applicant_ids[0]
            duplicate_domain = applicant_id.candidate_id._get_similar_candidates_domain()
            duplicates = self.env['hr.candidate'].search(duplicate_domain).applicant_ids
            refused_applications |= duplicates
            url = applicant_id._get_html_link()
            message = _(
                "Refused automatically because this application has been identified as a duplicate of %(link)s",
                link=url)
            duplicates._message_log_batch(bodies={duplicate.id: message for duplicate in duplicates})
        refused_applications.write({'refuse_reason_id': self.refuse_reason_id.id, 'active': False, 'refuse_date': datetime.now()})

        if self.send_mail:
            # TDE note: keeping 16.0 behavior, clean me please
            message_values = {
                'email_layout_xmlid' : 'hr_recruitment.mail_notification_light_without_background',
            }
            if len(self.applicant_ids) > 1:
                self.applicant_ids.with_context(active_test=True).message_mail_with_source(
                    self.template_id,
                    auto_delete_keep_log=True,
                    **message_values
                )
            else:
                self.applicant_ids.with_context(active_test=True).message_post_with_source(
                    self.template_id,
                    subtype_xmlid='mail.mt_note',
                    **message_values
                )

    @api.depends('applicant_ids')
    def _compute_duplicates_count(self):
        self.duplicates_count = self.applicant_ids.other_applications_count if len(self.applicant_ids) == 1 else 0
