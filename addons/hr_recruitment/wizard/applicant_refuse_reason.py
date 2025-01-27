# -*- coding: utf-8 -*-

from datetime import datetime
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ApplicantGetRefuseReason(models.TransientModel):
    _name = 'applicant.get.refuse.reason'
    _inherit = ['mail.composer.mixin']
    _description = 'Get Refuse Reason'

    def _default_refuse_reason_id(self):
        return self.env['hr.applicant.refuse.reason'].search([], limit=1)

    refuse_reason_id = fields.Many2one('hr.applicant.refuse.reason', 'Refuse Reason', required=True, default=_default_refuse_reason_id)
    applicant_ids = fields.Many2many('hr.applicant')
    send_mail = fields.Boolean("Send Email", default=True)
    template_id = fields.Many2one('mail.template', string='Email Template',
        related="refuse_reason_id.template_id", store=True, readonly=False,
        domain="[('model', '=', 'hr.applicant')]")
    applicant_without_email = fields.Text(compute='_compute_applicant_without_email',
        string='Applicant(s) not having email')
    applicant_emails = fields.Text(compute='_compute_applicant_emails')
    duplicates = fields.Boolean('Duplicates')
    duplicates_count = fields.Integer('Duplicates Count', compute='_compute_duplicates_count')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    @api.depends('refuse_reason_id')
    def _compute_template_id(self):
        for wizard in self:
            wizard.template_id = wizard.refuse_reason_id.template_id

    @api.depends('applicant_ids')
    def _compute_applicant_without_email(self):
        for wizard in self:
            applicants = wizard.applicant_ids.filtered(lambda x: not x.email_from and not x.partner_id.email)
            if applicants:
                wizard.applicant_without_email = "%s\n%s" % (
                    _("You can't select Send email option.\nThe email will not be sent to the following applicant(s) as they don't have an email address:"),
                    ", ".join([i.partner_name or i.display_name for i in applicants])
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

    @api.depends('applicant_ids')
    def _compute_duplicates_count(self):
        self.duplicates_count = self.applicant_ids.other_applications_count if len(self.applicant_ids) == 1 else 0

    # Overrides of mail.composer.mixin
    @api.depends('refuse_reason_id')  # fake trigger otherwise not computed in new mode
    def _compute_render_model(self):
        self.render_model = 'hr.applicant'

    def action_refuse_reason_apply(self):
        if self.send_mail:
            if not self.env.user.email:
                raise UserError(_("Unable to post message, please configure the sender's email address."))
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
            self._prepare_send_refusal_mails()

        return {'type': 'ir.actions.act_window_close'}

    def _prepare_send_refusal_mails(self):
        mail_values = []
        for applicant in self.applicant_ids:
            mail_values.append(self._prepare_mail_values(applicant))
        self.env['mail.mail'].sudo().create(mail_values)

    def _prepare_mail_values(self, applicant):
        """ Create mail specific for recipient """
        lang = self._render_lang(applicant.ids)[applicant.id]
        subject = self._render_field('subject', applicant.ids, set_lang=lang)[applicant.id]
        body = self._render_field('body', applicant.ids, set_lang=lang)[applicant.id]
        mail_values = {
            'attachment_ids': [(4, att.id) for att in self.attachment_ids],
            'author_id': self.env.user.partner_id.id,
            'auto_delete': self.template_id.auto_delete if self.template_id else True,
            'body_html': body,
            'email_to': applicant.email_from or applicant.partner_id.email,
            'email_from': self.env.user.email_formatted,
            'model': None,
            'res_id': None,
            'subject': subject,
        }

        return mail_values
