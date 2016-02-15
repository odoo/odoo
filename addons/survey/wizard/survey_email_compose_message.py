# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import urlparse
import uuid

from odoo import api, fields, models, _
from odoo.exceptions import UserError


emails_split = re.compile(r"[;,\n\r]+")


class SurveyMailComposeMessage(models.TransientModel):
    _name = 'survey.mail.compose.message'
    _inherit = 'mail.compose.message'
    _description = 'Email composition wizard for Survey'
    _log_access = True

    @api.model
    def default_get(self, fields):
        res = super(SurveyMailComposeMessage, self).default_get(fields)
        active_ids = self.env.context.get('active_ids')
        if self.env.context.get('active_model') == 'res.partner' and active_ids:
            res.update({'partner_ids': active_ids})
        return res

    survey_id = fields.Many2one('survey.survey', string='Survey', required=True,
                                default=lambda self: self.env.context.get('model') == 'survey.survey' and self.env.context.get('res_id') or None)
    public = fields.Selection([('public_link', 'Share the public web link to your audience.'),
                                ('email_public_link', 'Send by email the public web link to your audience.'),
                                ('email_private', 'Send private invitation to your audience (only one response per recipient and per invitation).')],
        string='Share options', required=True, default="public_link")
    public_url = fields.Char(related='survey_id.public_url')
    public_url_html = fields.Char(compute="_compute_public_url_html", string="Public HTML web link")
    partner_ids = fields.Many2many('res.partner',
        'survey_mail_compose_message_res_partner_rel',
        'wizard_id', 'partner_id', string='Existing contacts')
    attachment_ids = fields.Many2many('ir.attachment',
        'survey_mail_compose_message_ir_attachments_rel',
        'wizard_id', 'attachment_id', string='Attachments')
    multi_email = fields.Text(string='List of emails', help="This list of emails of recipients will not converted in contacts. Emails separated by commas, semicolons or newline.")
    date_deadline = fields.Date(string="Deadline to which the invitation to respond is valid", help="Deadline to which the invitation to respond for this survey is valid. If the field is empty, the invitation is still valid.")

    def _compute_public_url_html(self):
        """ Compute if the message is unread by the current user """
        for wizard in self:
            wizard.public_url_html = '<a href="%s">%s</a>' % (wizard.public_url, _("Click here to start survey"))

    @api.onchange('multi_email')
    def onchange_multi_email(self):
        emails = list(set(emails_split.split(self.multi_email or "")))
        emails_checked = []
        error_message = ""
        for email in emails:
            email = email.strip()
            if email:
                if not re.search(r"^[^@]+@[^@]+$", email):
                    error_message += "\n'%s'" % email
                else:
                    emails_checked.append(email)
        if error_message:
            raise UserError(_("One email at least is incorrect: %s") % error_message)

        emails_checked.sort()
        self.multi_email = '\n'.join(emails_checked)

    @api.onchange('survey_id')
    def onchange_survey_id(self):
        """ Compute if the message is unread by the current user. """
        if self.survey_id:
            self.subject = self.survey_id.title
            self.public_url = self.survey_id.public_url
            self.public_url_html = '<a href="%s">%s</a>' % (self.survey_id.public_url, _("Click here to take survey"))
        else:
            txt = _("Please select a survey")
            self.public_url = txt
            self.public_url_html = txt

    #------------------------------------------------------
    # Wizard validation and send
    #------------------------------------------------------

    @api.multi
    def send_mail(self, auto_commit=False):
        """ Process the wizard content and proceed with sending the related
            email(s), rendering any template patterns on the fly if needed """
        self.ensure_one()
        UserInput = self.env['survey.user_input']
        Partner = self.env['res.partner']
        Mail = self.env['mail.mail']
        anonymous = self.env.ref('portal.group_anonymous', raise_if_not_found=False)

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
            mail = Mail.create(values)
            mail.send()

        def create_token(wizard, partner_id, email):
            if self.env.context.get("survey_resent_token"):
                user_input = UserInput.search([('survey_id', '=', wizard.survey_id.id), ('state', 'in', ['new', 'skip']), '|', ('partner_id', '=', partner_id), ('email', '=', email)], limit=1)
                if user_input:
                    return user_input.token
            if wizard.public != 'email_private':
                return None
            else:
                token = uuid.uuid4().__str__()
                # create response with token
                UserInput.create({
                    'survey_id': wizard.survey_id.id,
                    'deadline': wizard.date_deadline,
                    'date_create': fields.Datetime.now(),
                    'type': 'link',
                    'state': 'new',
                    'token': token,
                    'partner_id': partner_id,
                    'email': email})
                return token

        # check if __URL__ is in the text
        if self.body.find("__URL__") < 0:
            raise UserError(_("The content of the text don't contain '__URL__'. \
                __URL__ is automaticaly converted into the special url of the survey."))

        if not self.multi_email and not self.partner_ids and (self.env.context.get('default_partner_ids') or self.env.context.get('default_multi_email')):
            self.multi_email = self.env.context.get('default_multi_email')
            self.partner_ids = self.env.context.get('default_partner_ids')

        # quick check of email list
        emails_list = []
        if self.multi_email:
            emails = list(set(emails_split.split(self.multi_email)) - set([partner.email for partner in self.partner_ids]))
            for email in emails:
                email = email.strip()
                if re.search(r"^[^@]+@[^@]+$", email):
                    emails_list.append(email)

        # remove public anonymous access
        partner_list = []
        for partner in self.partner_ids:
            if not anonymous or not partner.user_ids or anonymous not in [group.id for group in partner.user_ids[0].groups_id]:
                partner_list.append({'id': partner.id, 'email': partner.email})

        if not len(emails_list) and not len(partner_list):
            if self.model == 'res.partner' and self.res_id:
                return False
            raise UserError(_("Please enter at least one valid recipient."))

        for email in emails_list:
            partner = Partner.search([('email', '=', email)], limit=1)
            token = create_token(self, partner.id, email)
            create_response_and_send_mail(self, token, partner.id, email)

        for partner in partner_list:
            token = create_token(self, partner['id'], partner['email'])
            create_response_and_send_mail(self, token, partner['id'], partner['email'])

        return {'type': 'ir.actions.act_window_close'}
