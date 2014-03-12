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

from openerp import tools
from openerp import SUPERUSER_ID
from openerp.osv import osv
from openerp.osv import fields
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.translate import _

# main mako-like expression pattern
EXPRESSION_PATTERN = re.compile('(\$\{.+?\})')


class mail_compose_message(osv.TransientModel):
    """ Generic message composition wizard. You may inherit from this wizard
        at model and view levels to provide specific features.

        The behavior of the wizard depends on the composition_mode field:
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
                - default_parent_id or message_id or active_id: ID of the
                    mail.message we reply to
                - message.res_model or default_model
                - message.res_id or default_res_id
            - mass_mail: model and IDs of records the user mass-mails
                - active_ids: record IDs
                - default_model or active_model
        """
        if context is None:
            context = {}
        result = super(mail_compose_message, self).default_get(cr, uid, fields, context=context)
        # get some important values from context
        composition_mode = context.get('default_composition_mode', context.get('mail.compose.message.mode'))
        model = context.get('default_model', context.get('active_model'))
        res_id = context.get('default_res_id', context.get('active_id'))
        message_id = context.get('default_parent_id', context.get('message_id', context.get('active_id')))
        active_ids = context.get('active_ids')
        if 'active_domain' in context:  # not context.get() because we want to keep global [] domains
            result['use_active_domain'] = True
            result['active_domain'] = '%s' % context.get('active_domain')
        elif not result.get('active_domain'):
            result['active_domain'] = ''
        # get default values according to the composition mode
        if composition_mode == 'reply':
            vals = self.get_message_data(cr, uid, message_id, context=context)
        elif composition_mode == 'comment' and model and res_id:
            vals = self.get_record_data(cr, uid, model, res_id, context=context)
        elif composition_mode == 'mass_mail' and model and active_ids:
            vals = {'model': model, 'res_id': res_id}
        else:
            vals = {'model': model, 'res_id': res_id}
        if composition_mode:
            vals['composition_mode'] = composition_mode

        for field in vals:
            if field in fields:
                result[field] = vals[field]

        # TDE HACK: as mailboxes used default_model='res.users' and default_res_id=uid
        # (because of lack of an accessible pid), creating a message on its own
        # profile may crash (res_users does not allow writing on it)
        # Posting on its own profile works (res_users redirect to res_partner)
        # but when creating the mail.message to create the mail.compose.message
        # access rights issues may rise
        # We therefore directly change the model and res_id
        if result.get('model') == 'res.users' and result.get('res_id') == uid:
            result['model'] = 'res.partner'
            result['res_id'] = self.pool.get('res.users').browse(cr, uid, uid).partner_id.id
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
        'use_active_domain': fields.boolean('Use active domain'),
        'active_domain': fields.char('Active domain', readonly=True),
        'post': fields.boolean('Post a copy in the document',
            help='Post a copy of the message on the document communication history.'),
        'notify': fields.boolean('Notify followers',
            help='Notify followers of the document'),
        'same_thread': fields.boolean('Replies in the document',
            help='Replies to the messages will go into the selected document.'),
        'attachment_ids': fields.many2many('ir.attachment',
            'mail_compose_message_ir_attachments_rel',
            'wizard_id', 'attachment_id', 'Attachments'),
        'filter_id': fields.many2one('ir.filters', 'Filters'),
    }
    #TODO change same_thread to False in trunk (Require view update)
    _defaults = {
        'composition_mode': 'comment',
        'body': lambda self, cr, uid, ctx={}: '',
        'subject': lambda self, cr, uid, ctx={}: False,
        'partner_ids': lambda self, cr, uid, ctx={}: [],
        'post': False,
        'notify': False,
        'same_thread': True,
    }

    def check_access_rule(self, cr, uid, ids, operation, context=None):
        """ Access rules of mail.compose.message:
            - create: if
                - model, no res_id, I create a message in mass mail mode
            - then: fall back on mail.message acces rules
        """
        if isinstance(ids, (int, long)):
            ids = [ids]

        # Author condition (CREATE (mass_mail))
        if operation == 'create' and uid != SUPERUSER_ID:
            # read mail_compose_message.ids to have their values
            message_values = {}
            cr.execute('SELECT DISTINCT id, model, res_id FROM "%s" WHERE id = ANY (%%s) AND res_id = 0' % self._table, (ids,))
            for id, rmod, rid in cr.fetchall():
                message_values[id] = {'model': rmod, 'res_id': rid}
            # remove from the set to check the ids that mail_compose_message accepts
            author_ids = [mid for mid, message in message_values.iteritems()
                if message.get('model') and not message.get('res_id')]
            ids = list(set(ids) - set(author_ids))

        return super(mail_compose_message, self).check_access_rule(cr, uid, ids, operation, context=context)

    def _notify(self, cr, uid, newid, context=None, force_send=False, user_signature=True):
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
        doc_name_get = self.pool[model].name_get(cr, uid, [res_id], context=context)
        record_name = False
        if doc_name_get:
            record_name = doc_name_get[0][1]
        values = {
            'model': model,
            'res_id': res_id,
            'record_name': record_name,
        }
        if record_name:
            values['subject'] = 'Re: %s' % record_name
        return values

    def get_message_data(self, cr, uid, message_id, context=None):
        """ Returns a defaults-like dict with initial values for the composition
            wizard when replying to the given message (e.g. including the quote
            of the initial message, and the correct recipients).

            :param int message_id: id of the mail.message to which the user
                is replying.
        """
        if not message_id:
            return {}
        if context is None:
            context = {}
        message_data = self.pool.get('mail.message').browse(cr, uid, message_id, context=context)

        # create subject
        re_prefix = _('Re:')
        reply_subject = tools.ustr(message_data.subject or message_data.record_name or '')
        if not (reply_subject.startswith('Re:') or reply_subject.startswith(re_prefix)) and message_data.subject:
            reply_subject = "%s %s" % (re_prefix, reply_subject)
        # get partner_ids from original message
        partner_ids = [partner.id for partner in message_data.partner_ids] if message_data.partner_ids else []
        partner_ids += context.get('default_partner_ids', [])
        if context.get('is_private',False) and message_data.author_id : #check message is private then add author also in partner list.
            partner_ids += [message_data.author_id.id]
        # update the result
        result = {
            'record_name': message_data.record_name,
            'model': message_data.model,
            'res_id': message_data.res_id,
            'parent_id': message_data.id,
            'subject': reply_subject,
            'partner_ids': partner_ids,
        }
        return result

    #------------------------------------------------------
    # Wizard validation and send
    #------------------------------------------------------

    def send_mail(self, cr, uid, ids, context=None):
        """ Process the wizard content and proceed with sending the related
            email(s), rendering any template patterns on the fly if needed. """
        if context is None:
            context = {}
        # clean the context (hint: mass mailing sets some default values that
        # could be wrongly interpreted by mail_mail)
        context.pop('default_email_to', None)
        context.pop('default_partner_ids', None)

        active_ids = context.get('active_ids')
        is_log = context.get('mail_compose_log', False)

        for wizard in self.browse(cr, uid, ids, context=context):
            mass_mail_mode = wizard.composition_mode == 'mass_mail'
            active_model_pool = self.pool[wizard.model if wizard.model else 'mail.thread']
            if not hasattr(active_model_pool, 'message_post'):
                context['thread_model'] = wizard.model
                active_model_pool = self.pool['mail.thread']

            # wizard works in batch mode: [res_id] or active_ids or active_domain
            if mass_mail_mode and wizard.use_active_domain and wizard.model:
                res_ids = self.pool[wizard.model].search(cr, uid, eval(wizard.active_domain), context=context)
            elif mass_mail_mode and wizard.model and active_ids:
                res_ids = active_ids
            else:
                res_ids = [wizard.res_id]

            all_mail_values = self.get_mail_values(cr, uid, wizard, res_ids, context=context)

            for res_id, mail_values in all_mail_values.iteritems():
                if mass_mail_mode and not wizard.post:
                    m2m_attachment_ids = self.pool['mail.thread']._message_preprocess_attachments(
                        cr, uid, mail_values.pop('attachments', []),
                        mail_values.pop('attachment_ids', []),
                        'mail.message', 0,
                        context=context)
                    mail_values['attachment_ids'] = m2m_attachment_ids
                    if not mail_values.get('reply_to'):
                        mail_values['reply_to'] = mail_values['email_from']
                    self.pool.get('mail.mail').create(cr, uid, mail_values, context=context)
                else:
                    subtype = 'mail.mt_comment'
                    if is_log:  # log a note: subtype is False
                        subtype = False
                    elif mass_mail_mode:  # mass mail: is a log pushed to recipients unless specified, author not added
                        if not wizard.notify:
                            subtype = False
                        context = dict(context,
                                       mail_notify_force_send=False,  # do not send emails directly but use the queue instead
                                       mail_create_nosubscribe=True)  # add context key to avoid subscribing the author
                    active_model_pool.message_post(cr, uid, [res_id], type='comment', subtype=subtype, context=context, **mail_values)

        return {'type': 'ir.actions.act_window_close'}

    def get_mail_values(self, cr, uid, wizard, res_ids, context=None):
        """Generate the values that will be used by send_mail to create mail_messages
        or mail_mails. """
        results = dict.fromkeys(res_ids, False)
        mass_mail_mode = wizard.composition_mode == 'mass_mail'

        # render all template-based value at once
        if mass_mail_mode and wizard.model:
            rendered_values = self.render_message_batch(cr, uid, wizard, res_ids, context=context)

        for res_id in res_ids:
            # static wizard (mail.message) values
            mail_values = {
                'subject': wizard.subject,
                'body': wizard.body,
                'parent_id': wizard.parent_id and wizard.parent_id.id,
                'partner_ids': [partner.id for partner in wizard.partner_ids],
                'attachment_ids': [attach.id for attach in wizard.attachment_ids],
            }
            # mass mailing: rendering override wizard static values
            if mass_mail_mode and wizard.model:
                email_dict = rendered_values[res_id]
                mail_values['partner_ids'] += email_dict.pop('partner_ids', [])
                # process attachments: should not be encoded before being processed by message_post / mail_mail create
                attachments = []
                if email_dict.get('attachments'):
                    for name, enc_cont in email_dict.pop('attachments'):
                        attachments.append((name, base64.b64decode(enc_cont)))
                mail_values['attachments'] = attachments
                attachment_ids = []
                for attach_id in mail_values.pop('attachment_ids'):
                    new_attach_id = self.pool.get('ir.attachment').copy(cr, uid, attach_id, {'res_model': self._name, 'res_id': wizard.id}, context=context)
                    attachment_ids.append(new_attach_id)
                mail_values['attachment_ids'] = attachment_ids
                # email_from: mass mailing only can specify another email_from
                if email_dict.get('email_from'):
                    mail_values['email_from'] = email_dict.pop('email_from')
                # replies redirection: mass mailing only
                if wizard.same_thread and wizard.post:
                    email_dict.pop('reply_to', None)
                else:
                    mail_values['reply_to'] = email_dict.pop('reply_to', None)
                mail_values.update(email_dict)
            # mass mailing without post: mail_mail values
            if mass_mail_mode and not wizard.post:
                if 'mail_auto_delete' in context:
                    mail_values['auto_delete'] = context.get('mail_auto_delete')
                mail_values['body_html'] = mail_values.get('body', '')
                mail_values['recipient_ids'] = [(4, id) for id in mail_values.pop('partner_ids', [])]
            results[res_id] = mail_values
        return results

    def render_message_batch(self, cr, uid, wizard, res_ids, context=None):
        """Generate template-based values of wizard, for the document records given
        by res_ids. This method is meant to be inherited by email_template that
        will produce a more complete dictionary, using Jinja2 templates.

        Each template is generated for all res_ids, allowing to parse the template
        once, and render it multiple times. This is useful for mass mailing where
        template rendering represent a significant part of the process.

        :param browse wizard: current mail.compose.message browse record
        :param list res_ids: list of record ids

        :return dict results: for each res_id, the generated template values for
                              subject, body, email_from and reply_to
        """
        subjects = self.render_template_batch(cr, uid, wizard.subject, wizard.model, res_ids, context=context)
        bodies = self.render_template_batch(cr, uid, wizard.body, wizard.model, res_ids, context=context, post_process=True)
        emails_from = self.render_template_batch(cr, uid, wizard.email_from, wizard.model, res_ids, context=context)
        replies_to = self.render_template_batch(cr, uid, wizard.reply_to, wizard.model, res_ids, context=context)

        results = dict.fromkeys(res_ids, False)
        for res_id in res_ids:
            results[res_id] = {
                'subject': subjects[res_id],
                'body': bodies[res_id],
                'email_from': emails_from[res_id],
                'reply_to': replies_to[res_id],
            }
        return results

    def render_template_batch(self, cr, uid, template, model, res_ids, context=None, post_process=False):
        """ Render the given template text, replace mako-like expressions ``${expr}``
        with the result of evaluating these expressions with an evaluation context
        containing:

            * ``user``: browse_record of the current user
            * ``object``: browse_record of the document record this mail is
                          related to
            * ``context``: the context passed to the mail composition wizard

        :param str template: the template text to render
        :param str model: model name of the document record this mail is related to
        :param list res_ids: list of record ids
        """
        if context is None:
            context = {}
        results = dict.fromkeys(res_ids, False)

        for res_id in res_ids:
            def merge(match):
                exp = str(match.group()[2:-1]).strip()
                result = eval(exp, {
                    'user': self.pool.get('res.users').browse(cr, uid, uid, context=context),
                    'object': self.pool[model].browse(cr, uid, res_id, context=context),
                    'context': dict(context),  # copy context to prevent side-effects of eval
                })
                return result and tools.ustr(result) or ''
            results[res_id] = template and EXPRESSION_PATTERN.sub(merge, template)
        return results

    # Compatibility methods
    def render_template(self, cr, uid, template, model, res_id, context=None):
        return self.render_template_batch(cr, uid, template, model, [res_id], context)[res_id]

    def render_message(self, cr, uid, wizard, res_id, context=None):
        return self.render_message_batch(cr, uid, wizard, [res_id], context)[res_id]
