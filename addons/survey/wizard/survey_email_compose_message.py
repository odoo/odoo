# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-Today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from openerp.osv import osv
from openerp.osv import fields
from openerp.tools.translate import _
from datetime import datetime

import re
import uuid
import urlparse

emails_split = re.compile(r"[;,\n\r]+")


class survey_mail_compose_message(osv.TransientModel):
    _name = 'survey.mail.compose.message'
    _inherit = 'mail.compose.message'
    _description = 'Email composition wizard for Survey'
    _log_access = True

    def _get_public_url(self, cr, uid, ids, name, arg, context=None):
        res = dict((id, 0) for id in ids)
        survey_obj = self.pool.get('survey.survey')
        for wizard in self.browse(cr, uid, ids, context=context):
            res[wizard.id] = wizard.survey_id.public_url
        return res

    def _get_public_url_html(self, cr, uid, ids, name, arg, context=None):
        """ Compute if the message is unread by the current user """
        urls = self._get_public_url(cr, uid, ids, name, arg, context=context)
        for key, url in urls.items():
            urls[key] = '<a href="%s">%s</a>' % (url, _("Click here to start survey"))
        return urls

    _columns = {
        'survey_id': fields.many2one('survey.survey', 'Survey', required=True),
        'public': fields.selection([('public_link', 'Share the public web link to your audience.'),
                                    ('email_public_link', 'Send by email the public web link to your audience.'),
                                    ('email_private', 'Send private invitation to your audience (only one response per recipient and per invitation).')],
            string='Share options', required=True),
        'public_url': fields.function(_get_public_url, string="Public url", type="char"),
        'public_url_html': fields.function(_get_public_url_html, string="Public HTML web link", type="char"),
        'partner_ids': fields.many2many('res.partner',
            'survey_mail_compose_message_res_partner_rel',
            'wizard_id', 'partner_id', 'Existing contacts'),
        'attachment_ids': fields.many2many('ir.attachment',
            'survey_mail_compose_message_ir_attachments_rel',
            'wizard_id', 'attachment_id', 'Attachments'),
        'multi_email': fields.text(string='List of emails', help="This list of emails of recipients will not converted in contacts. Emails separated by commas, semicolons or newline."),
        'date_deadline': fields.date(string="Deadline to which the invitation to respond is valid", help="Deadline to which the invitation to respond for this survey is valid. If the field is empty, the invitation is still valid."),
    }

    _defaults = {
        'public': 'public_link',
        'survey_id': lambda self, cr, uid, ctx={}: ctx.get('model') == 'survey.survey' and ctx.get('res_id') or None
    }

    def default_get(self, cr, uid, fields, context=None):
        res = super(survey_mail_compose_message, self).default_get(cr, uid, fields, context=context)
        if context.get('active_model') == 'res.partner' and context.get('active_ids'):
            res.update({'partner_ids': context.get('active_ids')})
        return res

    def onchange_multi_email(self, cr, uid, ids, multi_email, context=None):
        emails = list(set(emails_split.split(multi_email or "")))
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
            raise osv.except_osv(_('Warning!'), _("One email at least is incorrect: %s" % error_message))

        emails_checked.sort()
        values = {'multi_email': '\n'.join(emails_checked)}
        return {'value': values}

    def onchange_survey_id(self, cr, uid, ids, survey_id, context=None):
        """ Compute if the message is unread by the current user. """
        if survey_id:
            survey = self.pool.get('survey.survey').browse(cr, uid, survey_id, context=context)
            return {
                'value': {
                    'subject': survey.title,
                    'public_url': survey.public_url,
                    'public_url_html': '<a href="%s">%s</a>' % (survey.public_url, _("Click here to take survey")),
                }}
        else:
            txt = _("Please select a survey")
            return {
                'value': {
                    'public_url': txt,
                    'public_url_html': txt,
                }}

    #------------------------------------------------------
    # Wizard validation and send
    #------------------------------------------------------

    def send_mail(self, cr, uid, ids, context=None):
        """ Process the wizard content and proceed with sending the related
            email(s), rendering any template patterns on the fly if needed """
        if context is None:
            context = {}

        survey_response_obj = self.pool.get('survey.user_input')
        partner_obj = self.pool.get('res.partner')
        mail_mail_obj = self.pool.get('mail.mail')
        try:
            model, anonymous_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'portal', 'group_anonymous')
        except ValueError:
            anonymous_id = None

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
                'partner_ids': partner_id and [(4, partner_id)] or None,
                'notified_partner_ids': partner_id and [(4, partner_id)] or None,
                'attachment_ids': wizard.attachment_ids or None,
                'email_from': wizard.email_from or None,
                'email_to': email,
            }
            mail_id = mail_mail_obj.create(cr, uid, values, context=context)
            mail_mail_obj.send(cr, uid, [mail_id], context=context)

        def create_token(wizard, partner_id, email):
            if context.get("survey_resent_token"):
                response_ids = survey_response_obj.search(cr, uid, [('survey_id', '=', wizard.survey_id.id), ('state', 'in', ['new', 'skip']), '|', ('partner_id', '=', partner_id), ('email', '=', email)], context=context)
                if response_ids:
                    return survey_response_obj.read(cr, uid, response_ids, ['token'], context=context)[0]['token']
            if wizard.public != 'email_private':
                return None
            else:
                token = uuid.uuid4().__str__()
                # create response with token
                survey_response_obj.create(cr, uid, {
                    'survey_id': wizard.survey_id.id,
                    'deadline': wizard.date_deadline,
                    'date_create': datetime.now(),
                    'type': 'link',
                    'state': 'new',
                    'token': token,
                    'partner_id': partner_id,
                    'email': email})
                return token

        for wizard in self.browse(cr, uid, ids, context=context):
            # check if __URL__ is in the text
            if wizard.body.find("__URL__") < 0:
                raise osv.except_osv(_('Warning!'), _("The content of the text don't contain '__URL__'. \
                    __URL__ is automaticaly converted into the special url of the survey."))

            if not wizard.multi_email and not wizard.partner_ids and (context.get('default_partner_ids') or context.get('default_multi_email')):
                wizard.multi_email = context.get('default_multi_email')
                wizard.partner_ids = context.get('default_partner_ids')

            # quick check of email list
            emails_list = []
            if wizard.multi_email:
                emails = list(set(emails_split.split(wizard.multi_email)) - set([partner.email for partner in wizard.partner_ids]))
                for email in emails:
                    email = email.strip()
                    if re.search(r"^[^@]+@[^@]+$", email):
                        emails_list.append(email)

            # remove public anonymous access
            partner_list = []
            for partner in wizard.partner_ids:
                if not anonymous_id or not partner.user_ids or anonymous_id not in [x.id for x in partner.user_ids[0].groups_id]:
                    partner_list.append({'id': partner.id, 'email': partner.email})

            if not len(emails_list) and not len(partner_list):
                if wizard.model == 'res.partner' and wizard.res_id:
                    return False
                raise osv.except_osv(_('Warning!'), _("Please enter at least one valid recipient."))

            for email in emails_list:
                partner_id = partner_obj.search(cr, uid, [('email', '=', email)], context=context)
                partner_id = partner_id and partner_id[0] or None
                token = create_token(wizard, partner_id, email)
                create_response_and_send_mail(wizard, token, partner_id, email)

            for partner in partner_list:
                token = create_token(wizard, partner['id'], partner['email'])
                create_response_and_send_mail(wizard, token, partner['id'], partner['email'])

        return {'type': 'ir.actions.act_window_close'}
