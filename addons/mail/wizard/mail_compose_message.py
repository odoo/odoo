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

import tools
from mail.mail_message import to_email
from osv import osv
from osv import fields
from tools.safe_eval import safe_eval as eval
from tools.safe_eval import literal_eval
from tools.translate import _

# main mako-like expression pattern
EXPRESSION_PATTERN = re.compile('(\$\{.+?\})')

class mail_compose_message(osv.osv_memory):
    """Generic E-mail composition wizard. This wizard is meant to be inherited
       at model and view level to provide specific wizard features.

       The behavior of the wizard can be modified through the use of context
       parameters, among which are:

         * mass_mail: turns multi-recipient mode, where the mail details can
                      contain template placeholders that will be merged with
                      actual data before being sent to each recipient, as
                      determined via  ``context['active_model']`` and
                      ``context['active_ids']``.
         * mail: if set to 'reply', the wizard will be in mail reply mode
         * active_model: model name of the document to which the mail being
                        composed is related
         * active_id: id of the document to which the mail being composed is
                      related, or id of the message to which user is replying,
                      in case mail == 'reply'.
         * active_ids: ids of the documents to which the mail being composed is
                      related, in case ``context['mass_mail']`` is set.
    """
    _name = 'mail.compose.message'
    _inherit = 'mail.message.common'
    _description = 'E-mail composition wizard'

    def default_get(self, cr, uid, fields, context=None):
        """Overridden to provide specific defaults depending on the context
           parameters.

           :param dict context: several context values will modify the behavior
                                of the wizard, cfr. the class description.
        """
        if context is None:
            context = {}
        result = super(mail_compose_message, self).default_get(cr, uid, fields, context=context)
        vals = {}
        if context.get('mass_mail'):
            return result
        if context.get('active_model') and context.get('active_id') and not context.get('mail')=='reply':
            vals = self.get_value(cr, uid, context.get('active_model'), context.get('active_id'), context)
        elif context.get('mail')=='reply' and context.get('active_id'):
            vals = self.get_message_data(cr, uid, int(context['active_id']), context)
        else:
            result['model'] = context.get('active_model', False)
        if not vals:
            return result
        for field in fields:
            result.update({field : vals.get(field, False)})
        return result

    _columns = {
        'attachment_ids': fields.many2many('ir.attachment','email_message_send_attachment_rel', 'wizard_id', 'attachment_id', 'Attachments'),
        'auto_delete': fields.boolean('Auto Delete', help="Permanently delete emails after sending"),
        'filter_id': fields.many2one('ir.filters', 'Filters'),
    }

    def get_value(self, cr, uid, model, res_id, context=None):
        """Returns a defaults-like dict with initial values for the composition
           wizard when sending an email related to the document record identified
           by ``model`` and ``res_id``.

           The default implementation returns an empty dictionary, and is meant
           to be overridden by subclasses.

           :param str model: model name of the document record this mail is related to.
           :param int res_id: id of the document record this mail is related to.
           :param dict context: several context values will modify the behavior
                                of the wizard, cfr. the class description.
        """
        return {}

    def get_message_data(self, cr, uid, message_id, context=None):
        """Returns a defaults-like dict with initial values for the composition
           wizard when replying to the given message (e.g. including the quote
           of the initial message, and the correct recipient).
           Should not be called unless ``context['mail'] == 'reply'``.

           :param int message_id: id of the mail.message to which the user
                                  is replying.
           :param dict context: several context values will modify the behavior
                                of the wizard, cfr. the class description.
                                When calling this method, the ``'mail'`` value
                                in the context should be ``'reply'``.
        """
        if context is None:
            context = {}
        result = {}
        mail_message = self.pool.get('mail.message')
        if message_id:
            message_data = mail_message.browse(cr, uid, message_id, context)
            subject = tools.ustr(message_data.subject or '')
            # we use the plain text version of the original mail, by default,
            # as it is easier to quote than the HTML version.
            # XXX TODO: make it possible to switch to HTML on the fly
            description = message_data.body_text or ''
            if context.get('mail') == 'reply':
                header = _('-------- Original Message --------')
                sender = _('From: %s')  % tools.ustr(message_data.email_from or '')
                email_to = _('To: %s') %  tools.ustr(message_data.email_to or '')
                sentdate = _('Date: %s') % message_data.date
                desc = '\n > \t %s' % tools.ustr(description.replace('\n', "\n > \t") or '')
                description = '\n'.join([header, sender, email_to, sentdate, desc])
                re_prefix = _("Re:")
                if not (subject.startswith('Re:') or subject.startswith(re_prefix)):
                    subject = "%s %s" % (re_prefix, subject)
            result.update({
                    'subtype' : 'plain', # default to the text version due to quoting
                    'body_text' : description,
                    'subject' : subject,
                    'message_id' :  message_data.message_id or False,
                    'attachment_ids' : [],
                    'res_id' : message_data.res_id or False,
                    'email_from' : message_data.email_to or False,
                    'email_to' : message_data.email_from or False,
                    'email_cc' : message_data.email_cc or False,
                    'email_bcc' : message_data.email_bcc or False,
                    'reply_to' : message_data.reply_to or False,
                    'model' : message_data.model or False,
                    'user_id' : message_data.user_id and message_data.user_id.id or False,
                    'references' : message_data.references and tools.ustr(message_data.references) or False,
                    'headers' : message_data.headers or False,
                })
        return result

    def send_mail(self, cr, uid, ids, context=None):
        '''Process the wizard contents and proceed with sending the corresponding
           email(s), rendering any template patterns on the fly if needed.
           The resulting email(s) are scheduled for being sent the next time the
           mail.message scheduler runs, or the next time
           ``mail.message.process_email_queue`` is called.

           :param dict context: several context values will modify the behavior
                                of the wizard, cfr. the class description.
        '''
        if context is None:
            context = {}
        mail_message = self.pool.get('mail.message')
        for mail in self.browse(cr, uid, ids, context=context):
            attachment = {}
            for attach in mail.attachment_ids:
                attachment[attach.datas_fname] = attach.datas
            references = False
            message_id = False

            # Reply Email
            if context.get('mail') == 'reply' and  mail.message_id:
                references = mail.references and mail.references + "," + mail.message_id or mail.message_id
            else:
                message_id = mail.message_id

            if context.get('mass_mail'):
                # Mass mailing: must render the template patterns
                if context.get('active_ids') and context.get('active_model'):
                    active_ids = context['active_ids']
                    active_model = context['active_model']
                else:
                    active_model = mail.model
                    active_model_pool = self.pool.get(active_model)
                    active_ids = active_model_pool.search(cr, uid, literal_eval(mail.filter_id.domain), context=literal_eval(mail.filter_id.context))

                for active_id in active_ids:
                    subject = self.render_template(cr, uid, mail.subject, active_model, active_id)

                    body =  mail.body_html if mail.subtype == 'html' else mail.body_text
                    body = self.render_template(cr, uid, body, active_model, active_id)
                    email_from = self.render_template(cr, uid, mail.email_from, active_model, active_id)
                    email_to = self.render_template(cr, uid, mail.email_to, active_model, active_id)
                    email_cc = self.render_template(cr, uid, mail.email_cc, active_model, active_id)
                    email_bcc = self.render_template(cr, uid, mail.email_bcc, active_model, active_id)
                    reply_to = self.render_template(cr, uid, mail.reply_to, active_model, active_id)

                    mail_message.schedule_with_attach(cr, uid, email_from, to_email(email_to), subject, body,
                        model=mail.model, email_cc=to_email(email_cc), email_bcc=to_email(email_bcc), reply_to=reply_to,
                        attachments=attachment, message_id=message_id, references=references, res_id=int(mail.res_id),
                        subtype=mail.subtype, headers=mail.headers, auto_delete=mail.auto_delete, context=context)
            else:
                # normal mode - no mass-mailing
                mail_message.schedule_with_attach(cr, uid, mail.email_from, to_email(mail.email_to), mail.subject, mail.body,
                    model=mail.model, email_cc=to_email(mail.email_cc), email_bcc=to_email(mail.email_bcc), reply_to=mail.reply_to,
                    attachments=attachment, message_id=message_id, references=references, res_id=int(mail.res_id),
                    subtype=mail.subtype, headers=mail.headers, auto_delete=mail.auto_delete, context=context)

        return {'type': 'ir.actions.act_window_close'}

    def render_template(self, cr, uid, template, model, res_id, context=None):
        """Render the given template text, replace mako-like expressions ``${expr}``
           with the result of evaluating these expressions with an evaluation context
           containing:

                * ``user``: browse_record of the current user
                * ``object``: browse_record of the document record this mail is
                              related to
                * ``context``: the context passed to the mail composition wizard

           :param str template: the template text to render
           :param str model: model name of the document record this mail is related to.
           :param int res_id: id of the document record this mail is related to.
        """
        if context is None:
            context = {}
        def merge(match):
            exp = str(match.group()[2:-1]).strip()
            result = eval(exp,
                          {
                            'user' : self.pool.get('res.users').browse(cr, uid, uid, context=context),
                            'object' : self.pool.get(model).browse(cr, uid, res_id, context=context),
                            'context': dict(context), # copy context to prevent side-effects of eval
                          })
            if result in (None, False):
                return ""
            return tools.ustr(result)
        return template and EXPRESSION_PATTERN.sub(merge, template)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
