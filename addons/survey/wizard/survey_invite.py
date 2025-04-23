# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
import logging
import re
import werkzeug

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.mail import email_split_and_format, email_normalize
from odoo.addons.mail.wizard.mail_compose_message import _reopen

_logger = logging.getLogger(__name__)

emails_split = re.compile(r"[;,\n\r]+")


class SurveyInvite(models.TransientModel):
    _name = 'survey.invite'
    _inherit = ['mail.composer.mixin']
    _description = 'Survey Invitation Wizard'

    @api.model
    def _get_default_author(self):
        return self.env.user.partner_id

    # composer content
    attachment_ids = fields.Many2many(
        'ir.attachment', 'survey_mail_compose_message_ir_attachments_rel', 'wizard_id', 'attachment_id',
        string='Attachments', compute='_compute_attachment_ids', store=True, readonly=False)
    # origin
    author_id = fields.Many2one(
        'res.partner', 'Author', index=True,
        ondelete='set null', default=_get_default_author)
    # recipients
    partner_ids = fields.Many2many(
        'res.partner', 'survey_invite_partner_ids', 'invite_id', 'partner_id', string='Recipients',
        domain="[ \
            '|', (survey_users_can_signup, '=', 1), \
            '|', (not survey_users_login_required, '=', 1), \
                 ('user_ids', '!=', False), \
        ]"
    )
    existing_partner_ids = fields.Many2many(
        'res.partner', compute='_compute_existing_partner_ids', readonly=True, store=False)
    emails = fields.Text(string='Additional emails')
    existing_emails = fields.Text(
        'Existing emails', compute='_compute_existing_emails',
        readonly=True, store=False)
    existing_mode = fields.Selection([
        ('new', 'New invite'), ('resend', 'Resend invite')],
        string='Handle existing', default='resend', required=True)
    existing_text = fields.Text('Resend Comment', compute='_compute_existing_text')
    # technical info
    mail_server_id = fields.Many2one('ir.mail_server', 'Outgoing mail server')
    # survey
    survey_id = fields.Many2one('survey.survey', string='Survey', required=True)
    survey_start_url = fields.Char('Survey URL', compute='_compute_survey_start_url')
    survey_access_mode = fields.Selection(related="survey_id.access_mode", readonly=True)
    survey_users_login_required = fields.Boolean(related="survey_id.users_login_required", readonly=True)
    survey_users_can_signup = fields.Boolean(related='survey_id.users_can_signup')
    deadline = fields.Datetime(string="Answer deadline")
    send_email = fields.Boolean(compute="_compute_send_email",
                                inverse="_inverse_send_email")
    survey_type = fields.Selection(related="survey_id.survey_type")
    scheduled_date = fields.Char(
        'Scheduled Date',
        compute="_compute_schedule_date", readonly=False, store=True,
        help="send emails after that date. This date is considered as being in UTC timezone."
    )
    model = fields.Char('Related Document Model', compute='_compute_model', readonly=False, store=True)
    res_ids = fields.Text('Related Document IDs', compute='_compute_res_ids', readonly=False, store=True)
    template_name = fields.Char('Template Name')  # used when saving a new mail template

    @api.depends('template_id')
    def _compute_schedule_date(self):
        for invite in self:
            if invite.template_id:
                invite.scheduled_date = invite.template_id.scheduled_date
            else:
                invite.scheduled_date = False

    @api.depends('survey_access_mode')
    def _compute_send_email(self):
        for record in self:
            record.send_email = record.survey_access_mode == 'token'

    def _inverse_send_email(self):
        pass

    @api.depends('partner_ids', 'survey_id')
    def _compute_existing_partner_ids(self):
        for wizard in self:
            wizard.existing_partner_ids = list(set(wizard.survey_id.user_input_ids.partner_id.ids) & set(wizard.partner_ids.ids))

    @api.depends('emails', 'survey_id')
    def _compute_existing_emails(self):
        for wizard in self:
            emails = list(set(emails_split.split(wizard.emails or "")))
            existing_emails = wizard.survey_id.mapped('user_input_ids.email')
            wizard.existing_emails = '\n'.join(email for email in emails if email in existing_emails)

    @api.depends('existing_partner_ids', 'existing_emails')
    def _compute_existing_text(self):
        for wizard in self:
            existing_text = False
            if wizard.existing_partner_ids:
                existing_text = '%s: %s.' % (
                    _('The following customers have already received an invite'),
                    ', '.join(wizard.mapped('existing_partner_ids.name'))
                )
            if wizard.existing_emails:
                existing_text = '%s\n' % existing_text if existing_text else ''
                existing_text += '%s: %s.' % (
                    _('The following emails have already received an invite'),
                    wizard.existing_emails
                )

            wizard.existing_text = existing_text

    @api.depends('survey_id.access_token')
    def _compute_survey_start_url(self):
        for invite in self:
            invite.survey_start_url = werkzeug.urls.url_join(invite.survey_id.get_base_url(), invite.survey_id.get_start_url()) if invite.survey_id else False

    # Overrides of mail.composer.mixin
    @api.depends('survey_id')  # fake trigger otherwise not computed in new mode
    def _compute_render_model(self):
        self.render_model = 'survey.user_input'

    @api.depends('template_id')
    def _compute_model(self):
        for invite in self:
            invite.model = 'survey.user_input'

    @api.depends('template_id')
    def _compute_res_ids(self):
        for invite in self:
            invite.res_ids = invite.survey_id.ids

    @api.onchange('emails')
    def _onchange_emails(self):
        if self.emails and (self.survey_users_login_required and not self.survey_id.users_can_signup):
            raise UserError(_('This survey does not allow external people to participate. You should create user accounts or update survey access mode accordingly.'))
        if not self.emails:
            return
        valid, error = [], []
        emails = list(set(emails_split.split(self.emails or "")))
        for email in emails:
            email_check = email_split_and_format(email)
            if not email_check:
                error.append(email)
            else:
                valid.extend(email_check)
        if error:
            raise UserError(_("Some emails you just entered are incorrect: %s", ', '.join(error)))
        self.emails = '\n'.join(valid)

    @api.onchange('partner_ids')
    def _onchange_partner_ids(self):
        if self.survey_users_login_required and self.partner_ids:
            if not self.survey_id.users_can_signup:
                invalid_partners = self.env['res.partner'].search([
                    ('user_ids', '=', False),
                    ('id', 'in', self.partner_ids.ids)
                ])
                if invalid_partners:
                    raise UserError(_(
                        'The following recipients have no user account: %s. You should create user accounts for them or allow external signup in configuration.',
                        ', '.join(invalid_partners.mapped('name'))
                    ))

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get('template_id') and not (values.get('body') or values.get('subject')):
                template = self.env['mail.template'].browse(values['template_id'])
                if not values.get('subject'):
                    values['subject'] = template.subject
                if not values.get('body'):
                    values['body'] = template.body_html
        return super().create(vals_list)

    @api.depends('template_id', 'partner_ids')
    def _compute_subject(self):
        for invite in self:
            if invite.subject:
                continue
            else:
                invite.subject = _("Participate to %(survey_name)s", survey_name=invite.survey_id.display_name)

    @api.depends('template_id', 'partner_ids')
    def _compute_body(self):
        for invite in self:
            langs = set(invite.partner_ids.mapped('lang')) - {False}
            if len(langs) == 1:
                invite = invite.with_context(lang=langs.pop())
            super(SurveyInvite, invite)._compute_body()

    @api.depends('template_id')
    def _compute_attachment_ids(self):
        """
        'OnChange-like' behavior used for template selection: not intended to update records when
            individual attachments get added
        """
        for invite in self:
            if invite.template_id:
                invite.attachment_ids = invite.template_id.attachment_ids
            else:
                invite.attachment_ids = False

    # ------------------------------------------------------
    # Wizard validation and send
    # ------------------------------------------------------

    def _prepare_answers(self, partners, emails):
        existing_answers = self.env['survey.user_input'].search([
            '&', ('survey_id', '=', self.survey_id.id),
            '|',
            ('partner_id', 'in', partners.ids),
            ('email', 'in', emails)
        ])
        partners_done, emails_done, answers = self._get_done_partners_emails(existing_answers)

        for new_partner in partners - partners_done:
            answers |= self.survey_id._create_answer(partner=new_partner, check_attempts=False, **self._get_answers_values())
        for new_email in [email for email in emails if email not in emails_done]:
            answers |= self.survey_id._create_answer(email=new_email, check_attempts=False, **self._get_answers_values())

        return answers

    def _get_done_partners_emails(self, existing_answers):
        answers = self.env['survey.user_input']
        partners_done = self.env['res.partner']
        emails_done = []
        if existing_answers:
            if self.existing_mode == 'resend':
                partners_done = existing_answers.mapped('partner_id')
                emails_done = existing_answers.mapped('email')

                # only add the last answer for each user of each type (partner_id & email)
                # to have only one mail sent per user
                for partner_done in partners_done:
                    answers |= next(existing_answer for existing_answer in
                        existing_answers.sorted(lambda answer: answer.create_date, reverse=True)
                        if existing_answer.partner_id == partner_done)

                for email_done in emails_done:
                    answers |= next(existing_answer for existing_answer in
                        existing_answers.sorted(lambda answer: answer.create_date, reverse=True)
                        if existing_answer.email == email_done)
        return (partners_done, emails_done, answers)

    def _get_answers_values(self):
        return {
            'deadline': self.deadline,
        }

    def _send_mail(self, answer):
        """ Create mail specific for recipient containing notably its access token """
        email_from = self.template_id._render_field('email_from', answer.ids)[answer.id] if self.template_id.email_from else self.author_id.email_formatted
        if not email_from:
            raise UserError(_("Unable to post message, please configure the sender's email address."))
        subject = self._render_field('subject', answer.ids)[answer.id]
        body = self._render_field('body', answer.ids)[answer.id]
        # post the message
        mail_values = {
            'attachment_ids': [(4, att.id) for att in self.attachment_ids],
            'auto_delete': True,
            'author_id': self.author_id.id,
            'body_html': body,
            'email_from': email_from,
            'model': None,
            'res_id': None,
            'subject': subject,
            'scheduled_date': self.scheduled_date,
        }
        if answer.partner_id:
            mail_values['recipient_ids'] = [(4, answer.partner_id.id)]
        else:
            mail_values['email_to'] = answer.email

        # optional support of default_email_layout_xmlid in context
        email_layout_xmlid = self.env.context.get('default_email_layout_xmlid', self.env.context.get('notif_layout'))
        if email_layout_xmlid:
            template_ctx = {
                'message': self.env['mail.message'].sudo().new(dict(body=mail_values['body_html'], record_name=self.survey_id.title)),
                'model_description': self.env['ir.model']._get('survey.survey').display_name,
                'company': self.env.company,
            }
            body = self.env['ir.qweb']._render(email_layout_xmlid, template_ctx, minimal_qcontext=True, raise_if_not_found=False)
            if body:
                mail_values['body_html'] = self.env['mail.render.mixin']._replace_local_links(body)
            else:
                _logger.warning('QWeb template %s not found or is empty when sending survey mails. Sending without layout', email_layout_xmlid)

        return self.env['mail.mail'].sudo().create(mail_values)

    def action_invite(self):
        """ Process the wizard content and proceed with sending the related
            email(s), rendering any template patterns on the fly if needed """
        self.ensure_one()
        if self.scheduled_date and self.deadline and \
            datetime.strptime(self.scheduled_date, "%Y-%m-%d %H:%M:%S") > self.deadline:
            raise UserError(_('The answer deadline should be greater than the Email Schedule Date.'))

        Partner = self.env['res.partner']

        # compute partners and emails, try to find partners for given emails
        valid_partners = self.partner_ids
        langs = set(valid_partners.mapped('lang')) - {False}
        if len(langs) == 1:
            self = self.with_context(lang=langs.pop())
        valid_emails = []
        for email in emails_split.split(self.emails or ''):
            partner = False
            email_normalized = email_normalize(email)
            if email_normalized:
                limit = None if self.survey_users_login_required else 1
                partner = Partner.search([('email_normalized', '=', email_normalized)], limit=limit)
            if partner:
                valid_partners |= partner
            else:
                email_formatted = email_split_and_format(email)
                if email_formatted:
                    valid_emails.extend(email_formatted)

        if not valid_partners and not valid_emails:
            raise UserError(_("Please enter at least one valid recipient."))

        answers = self._prepare_answers(valid_partners, valid_emails)
        for answer in answers:
            self._send_mail(answer)

        return {'type': 'ir.actions.act_window_close'}

    def open_template_creation_wizard(self):
        """ hit save as template button: opens a wizard that prompts for the template's subject.
            `create_mail_template` is called when saving the new wizard. """

        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_id': self.env.ref('mail.mail_compose_message_view_form_template_save').id,
            'name': _('Create a Mail Template'),
            'res_model': 'survey.invite',
            'context': {'dialog_size': 'medium'},
            'target': 'new',
            'res_id': self.id,
        }

    def create_mail_template(self):
        """ Creates a mail template with the current mail composer's fields. """
        self.ensure_one()
        if not self.model or not self.model in self.env:
            raise UserError(_('Template creation from composer requires a valid model.'))
        model_id = self.env['ir.model']._get_id(self.model)
        values = {
            'name': self.template_name or self.subject,
            'subject': self.subject,
            'body_html': self.body,
            'model_id': model_id,
            'use_default_to': True,
            'user_id': self.env.uid,
        }
        template = self.env['mail.template'].create(values)

        # generate the saved template
        self.write({'template_id': template.id})
        return _reopen(self, self.id, self.model, context={**self.env.context, 'dialog_size': 'large'})

    def cancel_save_template(self):
        """ Restore old subject when canceling the 'save as template' action
            as it was erased to let user give a more custom input. """
        self.ensure_one()
        return _reopen(self, self.id, self.model, context={**self.env.context, 'dialog_size': 'large'})
