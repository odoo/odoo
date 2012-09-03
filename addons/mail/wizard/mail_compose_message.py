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

import base64
import re
import tools

from osv import osv
from osv import fields
from tools.safe_eval import safe_eval as eval
from tools.translate import _

# main mako-like expression pattern
EXPRESSION_PATTERN = re.compile('(\$\{.+?\})')

class mail_compose_message(osv.TransientModel):
    """ Generic message composition wizard. You may inherit from this wizard
        at model and view levels to provide specific features.

        The behavior of the wizard can be modified through the context key 
        mail.compose.message.mode:
        - 'reply': reply to a previous message. The wizard is pre-populated 
            via ``get_message_data``.
        - 'comment': new post on a record. The wizard is pre-populated via
            ``get_record_data``
        - 'mass_mail': wizard in mass mailing mode where the mail details can
            contain template placeholders that will be merged with actual data
            before being sent to each recipient.
    """
    _name = 'mail.compose.message'
    _inherit = 'mail.message'
    _description = 'Email composition wizard'
    _log_access = True

    def default_get(self, cr, uid, fields, context=None):
        """ Handle composition mode. Some details about context keys:
            - comment: default mode, model and ID of a record the user comments
                - default_model or active_model
                - default_res_id or active_id
            - reply: active_id of a message the user replies to
                - active_id: ID of a mail.message to which we are replying
                - message.res_model or default_model
                - message.res_id or default_res_id
            - mass_mailing mode: model and IDs of records the user mass-mails
                - active_ids: record IDs
                - default_model or active_model
        """
        # get some important values from context
        if context is None:
            context = {}
        result = super(mail_compose_message, self).default_get(cr, uid, fields, context=context)

        # get some important values from context
        composition_mode = context.get('default_composition_mode', context.get('mail.compose.message.mode'))
        model = context.get('default_model', context.get('active_model'))
        res_id = context.get('default_res_id', context.get('active_id'))
        message_id = context.get('default_parent_id', context.get('message_id', context.get('active_id')))
        active_ids = context.get('active_ids')

        # get default values according to the composition mode
        if composition_mode == 'reply':
            vals = self.get_message_data(cr, uid, message_id, context=context)
        elif composition_mode == 'comment' and model and res_id:
            vals = self.get_record_data(cr, uid, model, res_id, context=context)
        elif composition_mode == 'mass_mail' and model and active_ids:
            vals = {'model': model, 'res_id': res_id, 'content_subtype': 'html'}
        else:
            vals = {'model': model, 'res_id': res_id}
        if composition_mode:
            vals['composition_mode'] = composition_mode

        for field in vals:
            if field in fields:
                result[field] = vals[field]
        return result

    def _get_composition_mode_selection(self, cr, uid, context=None):
        return [('comment', 'Comment a document'), ('reply', 'Reply to a message'), ('mass_mail', 'Mass mailing')]

    _columns = {
        'composition_mode': fields.selection(
            lambda s, *a, **k: s._get_composition_mode_selection(*a, **k),
            string='Composition mode'),
        'partner_ids': fields.many2many('res.partner',
            'mail_compose_message_res_partner_rel',
            'wizard_id', 'partner_id', 'Additional contacts'),
        'attachment_ids': fields.many2many('ir.attachment',
            'mail_compose_message_ir_attachments_rel',
            'wizard_id', 'attachment_id', 'Attachments'),
        'filter_id': fields.many2one('ir.filters', 'Filters'),
        'body_text': fields.text('Plain-text editor body'),
        'content_subtype': fields.char('Message content subtype', size=32, readonly=1,
            help="Type of message, usually 'html' or 'plain', used to select "\
                  "plain-text or rich-text contents accordingly"),
    }

    _defaults = {
        'composition_mode': 'comment',
        'content_subtype': lambda self,cr, uid, context={}: 'plain',
        'body_text': lambda self,cr, uid, context={}: False,
        'body': lambda self,cr, uid, context={}: '',
        'subject': lambda self,cr, uid, context={}: False,
    }

    def notify(self, cr, uid, newid, context=None):
        """ Override specific notify method of mail.message, because we do
            not want that feature in the wizard. """
        return

    def get_record_data(self, cr, uid, model, res_id, context=None):
        """ Returns a defaults-like dict with initial values for the composition
            wizard when sending an email related to the document record
            identified by ``model`` and ``res_id``.

            :param str model: model name of the document record this mail is
                related to.
            :param int res_id: id of the document record this mail is related to
        """
        return {'model': model, 'res_id': res_id}

    def get_message_data(self, cr, uid, message_id, context=None):
        """ Returns a defaults-like dict with initial values for the composition
            wizard when replying to the given message (e.g. including the quote
            of the initial message, and the correct recipients).

            :param int message_id: id of the mail.message to which the user
                is replying.
        """
        if context is None:
            context = {}
        result = {}
        if not message_id:
            return result

        current_user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        message_data = self.pool.get('mail.message').browse(cr, uid, message_id, context=context)

        # create subject
        re_prefix = _('Re:')
        reply_subject = tools.ustr(message_data.subject or '')
        if not (reply_subject.startswith('Re:') or reply_subject.startswith(re_prefix)):
            reply_subject = "%s %s" % (re_prefix, reply_subject)
        # create the reply in the body
        reply_header = _('On %(date)s, %(sender_name)s wrote:') % {
            'date': message_data.date if message_data.date else '',
            'sender_name': message_data.author_id.name }
        reply_body = '<div>%s<blockquote>%s</blockquote></div>' % (reply_header, message_data.body)
        # get partner_ids from original message
        partner_ids = [partner.id for partner in message_data.partner_ids] if message_data.partner_ids else []

        # update the result
        result.update({
            'model': message_data.model,
            'res_id': message_data.res_id,
            'parent_id': message_data.id,
            'body': reply_body,
            'subject': reply_subject,
            'partner_ids': partner_ids,
            'content_subtype': 'html',
        })
        return result

    def toggle_content_subtype(self, cr, uid, ids, context=None):
        """ hit toggle formatting mode button: calls onchange_formatting to 
            emulate an on_change, then writes the value to update the form. """
        for record in self.browse(cr, uid, ids, context=context):
            content_st_new_value = 'plain' if record.content_subtype == 'html' else 'html'
            onchange_res = self.onchange_content_subtype(cr, uid, ids, content_st_new_value, record.model, record.res_id, context=context)
            self.write(cr, uid, [record.id], onchange_res['value'], context=context)
        return True

    def onchange_content_subtype(self, cr, uid, ids, value, model, res_id, context=None):
        """ onchange_content_subtype (values: 'plain' or 'html'). This onchange
            on the subtype allows to have some specific behavior when switching
            between text or html mode.
            This method can be overridden for models that want to have their
            specific behavior. """
        return {'value': {'content_subtype': value}}

    def _verify_partner_email(self, cr, uid, partner_ids, context=None):
        """ Verify that selected partner_ids have an email_address defined.
            Otherwise throw a warning. """
        partner_wo_email_lst = []
        for partner in self.pool.get('res.partner').browse(cr, uid, partner_ids, context=context):
            if not partner.email:
                partner_wo_email_lst.append(partner)
        if not partner_wo_email_lst:
            return {}
        warning_msg = _('The following partners chosen as recipients for the email have no email address linked :')
        for partner in partner_wo_email_lst:
            warning_msg += '\n- %s' % (partner.name)
        return {'warning': {
                    'title': _('Partners email addresses not found'),
                    'message': warning_msg }
                }

    def onchange_partner_ids(self, cr, uid, ids, value, context=None):
        """ onchange_partner_ids (value format: [[6, False, [3, 4]]]). The
            basic purpose of this method is to check that destination partners
            effectively have email addresses. Otherwise a warning is thrown.
        """
        res = {'value': {}}
        if not value or not value[0] or not value[0][0] == 6:
            return 
        res.update(self._verify_partner_email(cr, uid, value[0][2], context=context))
        return res

    def unlink(self, cr, uid, ids, context=None):
        # Cascade delete all attachments, as they are owned by the composition wizard
        for wizard in self.read(cr, uid, ids, ['attachment_ids'], context=context):
            self.pool.get('ir.attachment').unlink(cr, uid, wizard['attachment_ids'], context=context)
        return super(mail_compose_message,self).unlink(cr, uid, ids, context=context)

    def dummy(self, cr, uid, ids, context=None):
        """ TDE: defined to have buttons that do basically nothing. It is
            currently impossible to have buttons that do nothing special
            in views (if type not specified, considered as 'object'). """
        return True

    #------------------------------------------------------
    # Wizard validation and send
    #------------------------------------------------------

    def send_mail(self, cr, uid, ids, context=None):
        """ Process the wizard content and proceed with sending the related
            email(s), rendering any template patterns on the fly if needed. """
        if context is None:
            context = {}
        active_ids = context.get('active_ids')

        for wizard in self.browse(cr, uid, ids, context=context):
            mass_mail_mode = wizard.composition_mode == 'mass_mail'
            active_model_pool = self.pool.get(wizard.model if wizard.model else 'mail.thread')

            # wizard works in batch mode: [res_id] or active_ids
            res_ids = active_ids if mass_mail_mode and wizard.model and active_ids else [wizard.res_id]
            for res_id in res_ids:
                # default values, according to the wizard options
                post_values = {
                    'subject': wizard.subject if wizard.content_subtype == 'html' else False,
                    'body': wizard.body if wizard.content_subtype == 'html' else '<pre>%s</pre>' % tools.ustr(wizard.body_text),
                    'partner_ids': [(4, partner.id) for partner in wizard.partner_ids],
                    'attachments': [(attach.name or attach.datas_fname, base64.b64decode(attach.datas)) for attach in wizard.attachment_ids],
                }
                # mass mailing: render and override default values
                if mass_mail_mode and wizard.model:
                    email_dict = self.render_message(cr, uid, wizard, wizard.model, res_id, context=context)
                    new_partner_ids = email_dict.pop('partner_ids', [])
                    post_values['partner_ids'] += new_partner_ids
                    new_attachments = email_dict.pop('attachments', [])
                    post_values['attachments'] += new_attachments
                    post_values.update(email_dict)
                # post the message
                active_model_pool.message_post(cr, uid, [res_id], msg_type='comment', context=context, **post_values)

        return {'type': 'ir.actions.act_window_close'}

    def render_message(self, cr, uid, wizard, model, res_id, context=None):
        """ Generate an email from the template for given (model, res_id) pair.
            This method is meant to be inherited by email_template that will
            produce a more complete dictionary, with email_to, ...
        """
        return {
            'subject': self.render_template(cr, uid, wizard.subject, model, res_id, context),
            'body': self.render_template(cr, uid, wizard.body, model, res_id, context),
        }

    def render_template(self, cr, uid, template, model, res_id, context=None):
        """ Render the given template text, replace mako-like expressions ``${expr}``
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
            result = eval(exp, {
                'user' : self.pool.get('res.users').browse(cr, uid, uid, context=context),
                'object' : self.pool.get(model).browse(cr, uid, res_id, context=context),
                'context': dict(context), # copy context to prevent side-effects of eval
                })
            return result and tools.ustr(result) or ''
        return template and EXPRESSION_PATTERN.sub(merge, template)
