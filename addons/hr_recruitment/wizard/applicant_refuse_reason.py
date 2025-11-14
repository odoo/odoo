from datetime import datetime
from itertools import product

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.fields import Domain


class ApplicantGetRefuseReason(models.TransientModel):
    _name = 'applicant.get.refuse.reason'
    _inherit = ['mail.composer.mixin']
    _description = 'Get Refuse Reason'

    def _default_refuse_reason_id(self):
        return self.env['hr.applicant.refuse.reason'].search([], limit=1)

    refuse_reason_id = fields.Many2one('hr.applicant.refuse.reason', 'Refuse Reason', required=True, default=_default_refuse_reason_id)
    applicant_ids = fields.Many2many('hr.applicant')
    send_mail = fields.Boolean("Send Email", compute='_compute_send_mail', precompute=True, store=True, readonly=False)
    template_id = fields.Many2one('mail.template', string='Email Template',
        compute='_compute_template_id', precompute=True, store=True, readonly=False,
        domain="[('model', '=', 'hr.applicant')]")
    applicant_without_email = fields.Text(compute='_compute_applicant_without_email',
        string='Applicant(s) not having email')
    duplicates = fields.Boolean(string='Refuse Duplicate Applications')
    duplicates_count = fields.Integer('Duplicates Count', compute='_compute_duplicate_applicant_ids_domain')
    duplicate_applicant_ids = fields.Many2many(
        'hr.applicant',
        relation='applicant_get_refuse_reason_duplicate_applicants_rel',
        string='Duplicate Applications',
        compute="_compute_duplicate_applicant_ids",
        store=True, readonly=False,
    )
    duplicate_applicant_ids_domain = fields.Binary(compute="_compute_duplicate_applicant_ids_domain")
    attachment_ids = fields.Many2many(
        'ir.attachment', string='Attachments',
        compute="_compute_from_template_id", readonly=False, store=True, bypass_search_access=True,
    )
    scheduled_date = fields.Char(
        'Scheduled Date',
        compute='_compute_from_template_id', readonly=False, store=True,
        help="send emails after that date. This date is considered as being in UTC timezone."
    )

    @api.depends('refuse_reason_id', 'applicant_without_email')
    def _compute_send_mail(self):
        for wizard in self:
            template = wizard.refuse_reason_id.template_id
            wizard.send_mail = template and not wizard.applicant_without_email

    @api.depends('applicant_ids')
    def _compute_applicant_without_email(self):
        for wizard in self:
            applicants = wizard.applicant_ids.filtered(lambda x: not x.email_from and not x.partner_id.email)
            if applicants:
                wizard.applicant_without_email = "%s\n%s" % (
                    _("You can't select Send email option.\nThe email will not be sent to the following applicant(s) as they don't have an email address:"),
                    ", ".join([i.partner_name or i.display_name or '' for i in applicants])
                )
            else:
                wizard.applicant_without_email = False

    @api.depends('applicant_ids')
    def _compute_duplicate_applicant_ids_domain(self):
        for wizard in self:
            domain = (
                self.applicant_ids._get_similar_applicants_domain()
                & Domain('id', 'not in', self.applicant_ids.ids)
                & Domain('application_status', 'not in', ['hired', 'refused', 'archived'])
            )
            wizard.duplicate_applicant_ids_domain = domain
            wizard.duplicates_count = self.env['hr.applicant'].search_count(wizard.duplicate_applicant_ids_domain)

    @api.depends('duplicates', 'duplicate_applicant_ids_domain')
    def _compute_duplicate_applicant_ids(self):
        if self.duplicates:
            self.duplicate_applicant_ids = self.env['hr.applicant'].search(self.duplicate_applicant_ids_domain)
        else:
            self.duplicate_applicant_ids = self.env['hr.applicant']

    # Overrides of mail.composer.mixin
    @api.depends('refuse_reason_id')  # fake trigger otherwise not computed in new mode
    def _compute_render_model(self):
        self.render_model = 'hr.applicant'

    @api.depends('refuse_reason_id')
    def _compute_template_id(self):
        for wizard in self:
            if wizard.refuse_reason_id:
                wizard.template_id = wizard.refuse_reason_id.template_id
            else:
                wizard.template_id = False

    @api.depends('template_id')
    def _compute_from_template_id(self):
        # wizard_field_name: template_field_name
        fields_to_copy_name_mapping = {
            'body': 'body_html',
            'attachment_ids': 'attachment_ids',
            'scheduled_date': 'scheduled_date',
            'subject': 'subject',
        }
        for wizard in self:
            for wizard_field_name, template_field_name in fields_to_copy_name_mapping.items():
                if wizard.template_id:
                    wizard[wizard_field_name] = wizard.template_id[template_field_name]
                else:
                    wizard[wizard_field_name] = False

    def action_refuse_reason_apply(self):
        if self.send_mail:
            if not self.env.user.email:
                raise UserError(_("Unable to post message, please configure the sender's email address."))
            if any(not (applicant.email_from or applicant.partner_id.email) for applicant in self.applicant_ids):
                raise UserError(_("At least one applicant doesn't have a email; you can't use send email option."))

        refused_applications = self.applicant_ids
        if self.duplicates_count and self.duplicates:
            refused_applications |= self.duplicate_applicant_ids

            original_applicant_by_duplicate_applicant = self._get_related_original_applicants()
            message_by_duplicate_applicant = {}
            for duplicate_applicant in self.duplicate_applicant_ids:
                url = original_applicant_by_duplicate_applicant[duplicate_applicant]._get_html_link()
                message_by_duplicate_applicant[duplicate_applicant.id] = _(
                    "Refused automatically because this application has been identified as a duplicate of %(link)s",
                    link=url)
            self.duplicate_applicant_ids._message_log_batch(bodies={
                    duplicate.id: message_by_duplicate_applicant[duplicate.id]
                    for duplicate in self.duplicate_applicant_ids
                }
            )
        refused_applications.write({'refuse_reason_id': self.refuse_reason_id.id, 'active': False, 'refuse_date': datetime.now()})

        if self.send_mail:
            self._prepare_send_refusal_mails()

        return {'type': 'ir.actions.act_window_close'}

    def _get_related_original_applicants(self):
        duplication_fields = ['id', 'email_normalized', 'partner_phone_sanitized', 'linkedin_profile']
        original_applicant_by_field_value = {field: {} for field in duplication_fields}
        related_original_applicants = dict()
        for original_applicant, field in product(self.applicant_ids, duplication_fields):
            value = original_applicant[field]
            if value:
                original_applicant_by_field_value[field][value] = original_applicant

        for duplicate_applicant in self.duplicate_applicant_ids:
            for field in duplication_fields:
                value = duplicate_applicant[field]
                if original_applicant_by_field_value[field].get(value):
                    related_original_applicants[duplicate_applicant] = original_applicant_by_field_value[field][value]
                    break
        return related_original_applicants

    def _prepare_send_refusal_mails(self):
        for applicant in self.applicant_ids:
            mail_values = self._prepare_mail_values(applicant)
            applicant.message_post(**mail_values)

    def _prepare_mail_values(self, applicant):
        """ Create mail specific for recipient """
        lang = self._render_lang(applicant.ids)[applicant.id]
        subject = self._render_field('subject', applicant.ids, set_lang=lang)[applicant.id]
        body = self._render_field('body', applicant.ids, set_lang=lang)[applicant.id]
        email_from = self.template_id.email_from if self.template_id and self.template_id.email_from else self.env.user.email_formatted
        return {
            'body': body,
            'email_from': email_from,
            'subject': subject,
            'author_id': self.env.user.partner_id.id,
            'incoming_email_to': applicant.email_from or applicant.partner_id.email,
            'scheduled_date': self.scheduled_date,
            'attachment_ids': [(4, att.id) for att in self.attachment_ids],
            'body_is_html': True,
        }
