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

import re
from urllib import urlencode
from urlparse import urljoin
from openerp.osv import osv
from openerp.osv import fields
from datetime import datetime
from openerp.tools.translate import _
import uuid


class survey_mail_compose_message(osv.TransientModel):
    _name = 'survey.mail.compose.message'
    _inherit = 'mail.compose.message'
    _description = 'Email composition wizard for Survey'
    _log_access = True

    _columns = {
        'partner_ids': fields.many2many('res.partner',
            'survey_mail_compose_message_res_partner_rel',
            'wizard_id', 'partner_id', 'Additional contacts'),
        'attachment_ids': fields.many2many('ir.attachment',
            'survey_mail_compose_message_ir_attachments_rel',
            'wizard_id', 'attachment_id', 'Attachments'),
        'multi_email': fields.text(string='List of emails', help="This list of emails of recipients will not converted in partner. Emails separated by commas, semicolons or newline."),
        'date_deadline': fields.date(string="Deadline date", help="Deadline to complete the survey. If the field is empty, the invitation is still valid."),
    }
    #------------------------------------------------------
    # Wizard validation and send
    #------------------------------------------------------

    def send_mail(self, cr, uid, ids, context=None):
        """ Process the wizard content and proceed with sending the related
            email(s), rendering any template patterns on the fly if needed. """
        if context is None:
            context = {}

        emails_split = re.compile(r"[;,\n\r]+")
        survey_response_obj = self.pool.get('survey.response')
        partner_obj = self.pool.get('res.partner')
        mail_mail_obj = self.pool.get('mail.mail')
        mail_message_obj = self.pool.get('mail.message')
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')

        def create_response_and_send_mail(wizard, token, partner_id, email):
            """ Create one mail by recipients and replace __URL__ by link with identification token
            """
            # create response with token
            survey_response_obj.create(cr, uid, {
                    'date_deadline': wizard.date_deadline,
                    'survey_id': wizard.res_id,
                    'date_create': datetime.now(),
                    'response_type': 'link',
                    'state': 'new',
                    'token': token,
                    'partner_id': partner_id,
                    'email': email,
                })

            # create url
            query = {
                'db': cr.dbname
            }
            fragment = {
                'active_id': wizard.res_id,
                'params': token,
                'action': 'survey.action_answer_survey',
            }
            url = urljoin(base_url, "?%s#%s" % (urlencode(query), urlencode(fragment)))

            # post the message
            values = {
                'model': 'survey',
                'res_id': wizard.res_id or False,
                'subject': wizard.subject,
                'body': wizard.body.replace("__URL__", url),
                'parent_id': None,
                'partner_ids': partner_id and [(4, partner_id)] or None,
                'notified_partner_ids': partner_id and [(4, partner_id)] or None,
                'attachment_ids': wizard.attachment_ids or None,
                'email_from': wizard.email_from or None,
                'email_to': email,
            }
            mail_obj = partner_id and mail_message_obj or mail_mail_obj
            mail_id = mail_obj.create(cr, uid, values, context=context)
            if mail_obj == mail_mail_obj:
                mail_obj.send(cr, uid, [mail_id], context=context)

        def create_token(wizard, partner_id, email):
            if context.get("survey_resent_token"):
                response_id = survey_response_obj.search(cr, uid, [('survey_id', '=', wizard.res_id), ('state', 'in', ['new', 'skip']), '|', ('partner_id', '=', partner_id), ('email', '=', email)], context=context)
                if response_id:
                    return survey_response_obj.search(cr, uid, response_id, ['token'], context=context)['token']
            return uuid.uuid4()

        for wizard in self.browse(cr, uid, ids, context=context):
            if wizard.model == 'survey':
                # check if __URL__ is in the text
                if wizard.body.find("__URL__") < 0:
                    raise osv.except_osv(_('Warning!'), _("The content of the text don't contain '__URL__'. \
                        __URL__ is automaticaly converted into the special url of the survey."))

                emails = list(set(emails_split.split(wizard.multi_email or "")) - set([partner.email for partner in wizard.partner_ids]))

                # quick check of email list
                emails_checked = []
                for email in emails:
                    email = email.strip()
                    if email:
                        if not re.search(r"^[^@]+@[^@]+$", email):
                            raise osv.except_osv(_('Warning!'), _("An email address is incorrect: '%s'" % email))
                        else:
                            emails_checked.append(email)
                if not len(emails_checked) and not len(wizard.partner_ids):
                    raise osv.except_osv(_('Warning!'), _("Please enter at least one recipient."))

                for email in emails_checked:
                    partner_id = partner_obj.search(cr, uid, [('email', '=', email)], context=context)
                    partner_id = partner_id and partner_id[0] or None
                    create_response_and_send_mail(wizard, token, partner_id, email)
                    token = create_token(wizard, partner_id, email)
                for partner in wizard.partner_ids:
                    token = create_token(wizard, partner.id, partner.email)
                    create_response_and_send_mail(wizard, token, partner.id, partner.email)

        return {'type': 'ir.actions.act_window_close'}
