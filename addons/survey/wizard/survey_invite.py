# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re
import uuid

from email.utils import formataddr
from werkzeug import urls

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

emails_split = re.compile(r"[;,\n\r]+")
email_validator = re.compile(r"[^@]+@[^@]+\.[^@]+")


class SurveyInvite(models.TransientModel):
    _name = 'survey.invite'
    _description = 'Survey Invitation Wizard'

    def default_survey_id(self):
        context = self.env.context
        if context.get('model') == 'survey.survey':
            return context.get('res_id')

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
    partner_ids = fields.Many2many('res.partner', 'survey_mail_compose_message_res_partner_rel', 'wizard_id', 'partner_id', string='Existing contacts')
    multi_email = fields.Text(string='List of emails', help="This list of emails of recipients will not be converted in contacts.\
        Emails must be separated by commas, semicolons or newline.")
    # technical info
    mail_server_id = fields.Many2one('ir.mail_server', 'Outgoing mail server')
    # survey
    survey_id = fields.Many2one('survey.survey', string='Survey', default=default_survey_id, required=True)
    public = fields.Selection([('public_link', 'Share the public web link to your audience.'),
                                ('email_public_link', 'Send by email the public web link to your audience.'),
                                ('email_private', 'Send private invitation to your audience (only one response per recipient and per invitation).')],
                                string='Share options', default='public_link', required=True)
    public_url = fields.Char(compute="_compute_survey_url", string="Public url")
    public_url_html = fields.Char(compute="_compute_survey_url", string="Public HTML web link")
    date_deadline = fields.Date(string="Deadline to which the invitation to respond is valid",
        help="Deadline to which the invitation to respond for this survey is valid. If the field is empty,\
        the invitation is still valid.")

    @api.depends('survey_id')
    def _compute_survey_url(self):
        for wizard in self:
            wizard.public_url = wizard.survey_id.public_url
            wizard.public_url_html = wizard.survey_id.public_url_html

    @api.model
    def default_get(self, fields):
        res = super(SurveyInvite, self).default_get(fields)
        context = self.env.context
        if context.get('active_model') == 'res.partner' and context.get('active_ids'):
            res.update({'partner_ids': context['active_ids']})
        return res

    @api.onchange('multi_email')
    def onchange_multi_email(self):
        emails = list(set(emails_split.split(self.multi_email or "")))
        emails_checked = []
        error_message = ""
        for email in emails:
            email = email.strip()
            if email:
                if not email_validator.match(email):
                    error_message += "\n'%s'" % email
                else:
                    emails_checked.append(email)
        if error_message:
            raise UserError(_("Incorrect Email Address: %s") % error_message)

        emails_checked.sort()
        self.multi_email = '\n'.join(emails_checked)

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

    @api.multi
    def send_mail_action(self):
        return self.send_mail()

    @api.multi
    def send_mail(self, auto_commit=False):
        """ Process the wizard content and proceed with sending the related
            email(s), rendering any template patterns on the fly if needed """

        SurveyUserInput = self.env['survey.user_input']
        Partner = self.env['res.partner']
        Mail = self.env['mail.mail']
        notif_layout = self.env.context.get('notif_layout', self.env.context.get('custom_layout'))

        def create_response_and_send_mail(wizard, token, partner_id, email):
            """ Create one mail by recipients and replace __URL__ by link with identification token """
            #set url
            url = wizard.survey_id.public_url

            if token:
                url = url + '/' + token

            # post the message
            values = {
                'model': None,
                'res_id': None,
                'subject': wizard.subject,
                'body': wizard.body.replace("__URL__", url),
                'body_html': wizard.body.replace("__URL__", url),
                'parent_id': None,
                'attachment_ids': wizard.attachment_ids and [(6, 0, wizard.attachment_ids.ids)] or None,
                'email_from': wizard.email_from or None,
                'auto_delete': True,
            }
            if partner_id:
                values['recipient_ids'] = [(4, partner_id)]
            else:
                values['email_to'] = email

            # optional support of notif_layout in context
            if notif_layout:
                try:
                    template = self.env.ref(notif_layout, raise_if_not_found=True)
                except ValueError:
                    _logger.warning('QWeb template %s not found when sending survey mails. Sending without layouting.' % (notif_layout))
                else:
                    template_ctx = {
                        'message': self.env['mail.message'].sudo().new(dict(body=values['body_html'], record_name=wizard.survey_id.title)),
                        'model_description': self.env['ir.model']._get('survey.survey').display_name,
                        'company': self.env.user.company_id,
                    }
                    body = template.render(template_ctx, engine='ir.qweb', minimal_qcontext=True)
                    values['body_html'] = self.env['mail.thread']._replace_local_links(body)

            Mail.create(values).send()

        def create_token(wizard, partner_id, email):
            if context.get("survey_resent_token"):
                survey_user_input = SurveyUserInput.search([('survey_id', '=', wizard.survey_id.id),
                    ('state', 'in', ['new', 'skip']), '|', ('partner_id', '=', partner_id),
                    ('email', '=', email)], limit=1)
                if survey_user_input:
                    return survey_user_input.token
            if wizard.public != 'email_private':
                return None
            else:
                token = str(uuid.uuid4())
                # create response with token
                survey_user_input = SurveyUserInput.create({
                    'survey_id': wizard.survey_id.id,
                    'deadline': wizard.date_deadline,
                    'date_create': fields.Datetime.now(),
                    'input_type': 'link',
                    'state': 'new',
                    'token': token,
                    'partner_id': partner_id,
                    'email': email})
                return survey_user_input.token

        for wizard in self:
            # check if __URL__ is in the text
            if wizard.body.find("__URL__") < 0:
                raise UserError(_("The content of the text don't contain '__URL__'. \
                    __URL__ is automaticaly converted into the special url of the survey."))

            context = self.env.context
            if not wizard.multi_email and not wizard.partner_ids and (context.get('default_partner_ids') or context.get('default_multi_email')):
                wizard.multi_email = context.get('default_multi_email')
                wizard.partner_ids = context.get('default_partner_ids')

            # quick check of email list
            emails_list = []
            if wizard.multi_email:
                emails = set(emails_split.split(wizard.multi_email)) - set(wizard.partner_ids.mapped('email'))
                for email in emails:
                    email = email.strip()
                    if email_validator.match(email):
                        emails_list.append(email)

            # remove public anonymous access
            partner_list = []
            for partner in wizard.partner_ids:
                partner_list.append({'id': partner.id, 'email': partner.email})

            if not len(emails_list) and not len(partner_list):
                raise UserError(_("Please enter at least one valid recipient."))

            for email in emails_list:
                partner = Partner.search([('email', '=', email)], limit=1)
                token = create_token(wizard, partner.id, email)
                create_response_and_send_mail(wizard, token, partner.id, email)

            for partner in partner_list:
                token = create_token(wizard, partner['id'], partner['email'])
                create_response_and_send_mail(wizard, token, partner['id'], partner['email'])

        return {'type': 'ir.actions.act_window_close'}
