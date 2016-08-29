# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import uuid
import urlparse

from odoo import api, fields, models, _
from odoo.exceptions import UserError

emails_split = re.compile(r"[;,\n\r]+")
email_validator = re.compile(r"[^@]+@[^@]+\.[^@]+")

class SurveyMailComposeMessage(models.TransientModel):
    _name = 'survey.mail.compose.message'
    _inherit = 'mail.compose.message'
    _description = 'Email composition wizard for Survey'

    def default_survey_id(self):
        context = self.env.context
        if context.get('model') == 'survey.survey':
            return context.get('res_id')

    survey_id = fields.Many2one('survey.survey', string='Survey', default=default_survey_id, required=True)
    public = fields.Selection([('public_link', 'Share the public web link to your audience.'),
                                ('email_public_link', 'Send by email the public web link to your audience.'),
                                ('email_private', 'Send private invitation to your audience (only one response per recipient and per invitation).')],
                                string='Share options', default='public_link', required=True)
    public_url = fields.Char(compute="_compute_survey_url", string="Public url")
    public_url_html = fields.Char(compute="_compute_survey_url", string="Public HTML web link")
    partner_ids = fields.Many2many('res.partner', 'survey_mail_compose_message_res_partner_rel', 'wizard_id', 'partner_id', string='Existing contacts')
    attachment_ids = fields.Many2many('ir.attachment', 'survey_mail_compose_message_ir_attachments_rel', 'wizard_id', 'attachment_id', string='Attachments')
    multi_email = fields.Text(string='List of emails', help="This list of emails of recipients will not be converted in contacts.\
        Emails must be separated by commas, semicolons or newline.")
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
        res = super(SurveyMailComposeMessage, self).default_get(fields)
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

    #------------------------------------------------------
    # Wizard validation and send
    #------------------------------------------------------
    @api.multi
    def send_mail(self, auto_commit=False):
        """ Process the wizard content and proceed with sending the related
            email(s), rendering any template patterns on the fly if needed """

        SurveyUserInput = self.env['survey.user_input']
        Partner = self.env['res.partner']
        Mail = self.env['mail.mail']
        anonymous_group = self.env.ref('portal.group_anonymous', raise_if_not_found=False)

        def create_response_and_send_mail(wizard, token, partner_id, email):
            """ Create one mail by recipients and replace __URL__ by link with identification token """
            #set url
            url = wizard.survey_id.public_url

            url = urlparse.urlparse(url).path[1:]  # dirty hack to avoid incorrect urls

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
                token = uuid.uuid4().__str__()
                # create response with token
                survey_user_input = SurveyUserInput.create({
                    'survey_id': wizard.survey_id.id,
                    'deadline': wizard.date_deadline,
                    'date_create': fields.Datetime.now(),
                    'type': 'link',
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
                if not anonymous_group or not partner.user_ids or anonymous_group not in partner.user_ids[0].groups_id:
                    partner_list.append({'id': partner.id, 'email': partner.email})

            if not len(emails_list) and not len(partner_list):
                if wizard.model == 'res.partner' and wizard.res_id:
                    return False
                raise UserError(_("Please enter at least one valid recipient."))

            for email in emails_list:
                partner = Partner.search([('email', '=', email)], limit=1)
                token = create_token(wizard, partner.id, email)
                create_response_and_send_mail(wizard, token, partner.id, email)

            for partner in partner_list:
                token = create_token(wizard, partner['id'], partner['email'])
                create_response_and_send_mail(wizard, token, partner['id'], partner['email'])

        return {'type': 'ir.actions.act_window_close'}
