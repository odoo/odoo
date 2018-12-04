# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

from email.utils import formataddr

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

emails_split = re.compile(r"[;,\n\r]+")


class SurveyInvite(models.TransientModel):
    _name = 'survey.invite'
    _description = 'Survey Invitation Wizard'

    @api.model
    def _get_default_from(self):
        if self.env.user.email:
            return formataddr((self.env.user.name, self.env.user.email))
        raise UserError(_("Unable to post message, please configure the sender's email address."))

    @api.model
    def _get_default_author(self):
        return self.env.user.partner_id

    # composer content
    subject = fields.Char('Subject')
    body = fields.Html('Contents', default='', sanitize_style=True)
    attachment_ids = fields.Many2many(
        'ir.attachment', 'survey_mail_compose_message_ir_attachments_rel', 'wizard_id', 'attachment_id',
        string='Attachments')
    template_id = fields.Many2one(
        'mail.template', 'Use template', index=True,
        domain="[('model', '=', 'survey.survey')]")
    # origin
    email_from = fields.Char('From', default=_get_default_from, help="Email address of the sender.")
    author_id = fields.Many2one(
        'res.partner', 'Author', index=True,
        ondelete='set null', default=_get_default_author,
        help="Author of the message.")
    # recipients
    partner_ids = fields.Many2many(
        'res.partner', 'survey_mail_compose_message_res_partner_rel', 'wizard_id', 'partner_id', string='Recipients')
    emails = fields.Text(string='Additional emails', help="This list of emails of recipients will not be converted in contacts.\
        Emails must be separated by commas, semicolons or newline.")
    existing_mode = fields.Selection([
        ('skip', 'Skip'), ('resend', 'Resend'), ('prevent', 'Prevent')],
        string='Existing', default='skip')
    # technical info
    mail_server_id = fields.Many2one('ir.mail_server', 'Outgoing mail server')
    # survey
    survey_id = fields.Many2one('survey.survey', string='Survey', required=True)
    survey_url = fields.Char(related="survey_id.public_url", readonly=True)
    survey_access_mode = fields.Selection(related="survey_id.access_mode", readonly=True)
    deadline = fields.Datetime(string="Answer deadline")

    @api.onchange('emails')
    def _onchange_emails(self):
        if self.emails and (self.survey_access_mode == 'internal' or (self.survey_access_mode == 'authentication' and not self.survey_id.users_can_signup)):
            raise UserError(_('This survey does not allow external people to participate. You should create user accounts or update survey access mode accordingly.'))
        if not self.emails:
            return
        valid, error = [], []
        emails = list(set(emails_split.split(self.emails or "")))
        for email in emails:
            email_check = tools.email_split_and_format(email)
            if not email_check:
                error.append(email)
            else:
                valid.extend(email_check)
        if error:
            raise UserError(_("Some emails you just entered are incorrect: %s") % (', '.join(error)))
        self.emails = '\n'.join(valid)

    @api.onchange('survey_access_mode')
    def _onchange_survey_access_mode(self):
        if self.survey_access_mode == 'internal':
            return {'domain': {
                    'partner_ids': [('user_ids.groups_id', 'in', [self.env.ref('base.group_user').id])]
                    }}
        elif self.survey_access_mode == 'authentication':
            if not self.survey_id.users_can_signup:
                return {'domain': {
                    'partner_ids': [('user_ids.groups_id', 'in', [self.env.ref('base.group_user').id, self.env.ref('base.group_portal').id])]
                    }}

    @api.onchange('partner_ids')
    def _onchange_partner_ids(self):
        if self.survey_access_mode == 'internal' and self.partner_ids:
            invalid_partners = self.partner_ids.filtered(lambda partner: not partner.user_ids or not all(user.has_group('base.group_user') for user in partner.user_ids))
            if invalid_partners:
                raise UserError(
                    _('The following recipients are not valid users belonging to the employee group: %s. You should create user accounts for them.' %
                        (','.join(invalid_partners.mapped('name')))))
        elif self.survey_access_mode == 'authentication' and self.partner_ids:
            if not self.survey_id.users_can_signup:
                invalid_partners = self.env['res.partner'].search([
                    ('user_ids', '=', False),
                    ('id', 'in', self.partner_ids.ids)
                ])
                if invalid_partners:
                    raise UserError(
                        _('The following recipients have no user account: %s. You should create user accounts for them or allow external signup in configuration.' %
                            (','.join(invalid_partners.mapped('name')))))

    @api.onchange('template_id', 'survey_id')
    def _onchange_template_id(self):
        """ UPDATE ME """
        to_render_fields = [
            'subject', 'body_html',
            'email_from', 'reply_to',
            'partner_to', 'email_to', 'email_cc',
            'attachment_ids',
            'mail_server_id'
        ]
        returned_fields = to_render_fields + ['partner_ids', 'attachments']
        for wizard in self:
            if wizard.template_id:
                values = {}

                template_values = wizard.template_id.generate_email([wizard.survey_id.id], fields=to_render_fields)[wizard.survey_id.id]
                values = dict((field, template_values[field]) for field in returned_fields if template_values.get(field))
                values['body'] = values.pop('body_html', '')

                # transform attachments into attachment_ids; not attached to the document because this will
                # be done further in the posting process, allowing to clean database if email not send
                Attachment = self.env['ir.attachment']
                for attach_fname, attach_datas in values.pop('attachments', []):
                    data_attach = {
                        'name': attach_fname,
                        'datas': attach_datas,
                        'datas_fname': attach_fname,
                        'res_model': 'mail.compose.message',  # TDE CHECKME
                        'res_id': 0,
                        'type': 'binary',  # override default_type from context, possibly meant for another model!
                    }
                    values.setdefault('attachment_ids', list()).append(Attachment.create(data_attach).id)
            else:
                default_values = self.default_get(returned_fields)
                values = dict((key, default_values[key]) for key in returned_fields if key in default_values)

            # This onchange should return command instead of ids for x2many field.
            # ORM handle the assignation of command list on new onchange (api.v8),
            # this force the complete replacement of x2many field with
            # command and is compatible with onchange api.v7
            values = self._convert_to_write(values)
            wizard.update(values)

    #------------------------------------------------------
    # Wizard validation and send
    #------------------------------------------------------

    def _prepare_answers(self, partners, emails):
        answers = self.env['survey.user_input']
        existing_answers = self.env['survey.user_input'].search([
            '&', ('survey_id', '=', self.survey_id.id),
            '|',
            ('partner_id', 'in', partners.ids),
            ('email', 'in', emails)
        ])
        partners_done = self.env['res.partner']
        emails_done = []
        if existing_answers:
            if self.existing_mode == 'prevent':
                raise UserError(_('Some of recipients already started survey. Please update recipients list accordingly.'))

            if self.existing_mode in ['skip', 'reset']:
                partners_done = existing_answers.mapped('partner_id')
                emails_done = existing_answers.mapped('email')

            if self.existing_mode == 'reset':
                existing_answers.write({
                    'deadline': self.deadline,
                    'state': 'new',
                    'user_input_line_ids': [(5, 0)],
                })
                answers |= existing_answers

        for new_partner in partners - partners_done:
            answers |= self.survey_id._create_answer(partner=new_partner, deadline=self.deadline)
        for new_email in [email for email in emails if email not in emails_done]:
            answers |= self.survey_id._create_answer(email=new_email, deadline=self.deadline)

        return answers

    def _send_mail(self, answer):
        """ Create mail specific for recipient containing notably its access token """
        url = '%s?token=%s' % (self.survey_id.public_url, answer.token)

        # post the message
        mail_values = {
            'email_from': self.email_from,
            'author_id': self.author_id.id,
            'model': None,
            'res_id': None,
            'subject': self.subject,
            'body_html': self.body.replace("__URL__", url),
            'attachment_ids': [(4, att.id) for att in self.attachment_ids],
            'auto_delete': True,
        }
        if answer.partner_id:
            mail_values['recipient_ids'] = [(4, answer.partner_id.id)]
        else:
            mail_values['email_to'] = answer.email

        # optional support of notif_layout in context
        notif_layout = self.env.context.get('notif_layout', self.env.context.get('custom_layout'))
        if notif_layout:
            try:
                template = self.env.ref(notif_layout, raise_if_not_found=True)
            except ValueError:
                _logger.warning('QWeb template %s not found when sending survey mails. Sending without layouting.' % (notif_layout))
            else:
                template_ctx = {
                    'message': self.env['mail.message'].sudo().new(dict(body=mail_values['body_html'], record_name=self.survey_id.title)),
                    'model_description': self.env['ir.model']._get('survey.survey').display_name,
                    'company': self.env.user.company_id,
                }
                body = template.render(template_ctx, engine='ir.qweb', minimal_qcontext=True)
                mail_values['body_html'] = self.env['mail.thread']._replace_local_links(body)

        return self.env['mail.mail'].sudo().create(mail_values)

    @api.multi
    def action_invite(self):
        """ Process the wizard content and proceed with sending the related
            email(s), rendering any template patterns on the fly if needed """
        self.ensure_one()
        Partner = self.env['res.partner']

        # check if __URL__ is in the text
        if self.body.find("__URL__") < 0:
            raise UserError(_("The content of the text don't contain '__URL__'. \
                __URL__ is automaticaly converted into the special url of the survey."))

        # compute partners and emails, try to find partners for given emails
        valid_partners = self.partner_ids
        valid_emails = []
        for email in emails_split.split(self.emails or ''):
            partner = False
            email_normalized = tools.email_normalize(email)
            if email_normalized:
                partner = Partner.search([('email_normalized', '=', email_normalized)])
            if partner:
                valid_partners |= partner
            else:
                email_formatted = tools.email_split_and_format(email)
                if email_formatted:
                    valid_emails.extend(email_formatted)

        if not valid_partners and not valid_emails:
            raise UserError(_("Please enter at least one valid recipient."))

        answers = self._prepare_answers(valid_partners, valid_emails)
        for answer in answers:
            self._send_mail(answer)

        return {'type': 'ir.actions.act_window_close'}
