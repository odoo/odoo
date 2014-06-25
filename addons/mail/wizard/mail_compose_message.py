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
        - 'comment': post on a record. The wizard is pre-populated via ``get_record_data``
        - 'mass_mail': wizard in mass mailing mode where the mail details can
            contain template placeholders that will be merged with actual data
            before being sent to each recipient.
    """
    _name = 'mail.compose.message'
    _inherit = 'mail.message'
    _description = 'Email composition wizard'
    _log_access = True
    _batch_size = 500

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

        # v6.1 compatibility mode
        result['composition_mode'] = result.get('composition_mode', context.get('mail.compose.message.mode'))
        result['model'] = result.get('model', context.get('active_model'))
        result['res_id'] = result.get('res_id', context.get('active_id'))
        result['parent_id'] = result.get('parent_id', context.get('message_id'))

        # default values according to composition mode - NOTE: reply is deprecated, fall back on comment
        if result['composition_mode'] == 'reply':
            result['composition_mode'] = 'comment'
        vals = {}
        if 'active_domain' in context:  # not context.get() because we want to keep global [] domains
            vals['use_active_domain'] = True
            vals['active_domain'] = '%s' % context.get('active_domain')
        if result['composition_mode'] == 'comment':
            vals.update(self.get_record_data(cr, uid, result, context=context))

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
        if result['model'] == 'res.users' and result['res_id'] == uid:
            result['model'] = 'res.partner'
            result['res_id'] = self.pool.get('res.users').browse(cr, uid, uid).partner_id.id
        return result

    def _get_composition_mode_selection(self, cr, uid, context=None):
        return [('comment', 'Post on a document'),
                ('mass_mail', 'Email Mass Mailing'),
                ('mass_post', 'Post on Multiple Documents')]

    _columns = {
        'composition_mode': fields.selection(
            lambda s, *a, **k: s._get_composition_mode_selection(*a, **k),
            string='Composition mode'),
        'partner_ids': fields.many2many('res.partner',
            'mail_compose_message_res_partner_rel',
            'wizard_id', 'partner_id', 'Additional Contacts'),
        'use_active_domain': fields.boolean('Use active domain'),
        'active_domain': fields.char('Active domain', readonly=True),
        'attachment_ids': fields.many2many('ir.attachment',
            'mail_compose_message_ir_attachments_rel',
            'wizard_id', 'attachment_id', 'Attachments'),
        'is_log': fields.boolean('Log an Internal Note',
                                 help='Whether the message is an internal note (comment mode only)'),
        # mass mode options
        'notify': fields.boolean('Notify followers',
            help='Notify followers of the document (mass post only)'),
    }
    _defaults = {
        'composition_mode': 'comment',
        'body': lambda self, cr, uid, ctx={}: '',
        'subject': lambda self, cr, uid, ctx={}: False,
        'partner_ids': lambda self, cr, uid, ctx={}: [],
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

    def get_record_data(self, cr, uid, values, context=None):
        """ Returns a defaults-like dict with initial values for the composition
        wizard when sending an email related a previous email (parent_id) or
        a document (model, res_id). This is based on previously computed default
        values. """
        if context is None:
            context = {}
        result, subject = {}, False
        if values.get('parent_id'):
            parent = self.pool.get('mail.message').browse(cr, uid, values.get('parent_id'), context=context)
            result['record_name'] = parent.record_name,
            subject = tools.ustr(parent.subject or parent.record_name or '')
            if not values.get('model'):
                result['model'] = parent.model
            if not values.get('res_id'):
                result['res_id'] = parent.res_id
            partner_ids = values.get('partner_ids', list()) + [partner.id for partner in parent.partner_ids]
            if context.get('is_private') and parent.author_id:  # check message is private then add author also in partner list.
                partner_ids += [parent.author_id.id]
            result['partner_ids'] = partner_ids
        elif values.get('model') and values.get('res_id'):
            doc_name_get = self.pool[values.get('model')].name_get(cr, uid, [values.get('res_id')], context=context)
            result['record_name'] = doc_name_get and doc_name_get[0][1] or ''
            subject = tools.ustr(result['record_name'])

        re_prefix = _('Re:')
        if subject and not (subject.startswith('Re:') or subject.startswith(re_prefix)):
            subject = "%s %s" % (re_prefix, subject)
        result['subject'] = subject

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

        for wizard in self.browse(cr, uid, ids, context=context):
            mass_mode = wizard.composition_mode in ('mass_mail', 'mass_post')
            active_model_pool = self.pool[wizard.model if wizard.model else 'mail.thread']
            if not hasattr(active_model_pool, 'message_post'):
                context['thread_model'] = wizard.model
                active_model_pool = self.pool['mail.thread']

            # wizard works in batch mode: [res_id] or active_ids or active_domain
            if mass_mode and wizard.use_active_domain and wizard.model:
                res_ids = self.pool[wizard.model].search(cr, uid, eval(wizard.active_domain), context=context)
            elif mass_mode and wizard.model and context.get('active_ids'):
                res_ids = context['active_ids']
            else:
                res_ids = [wizard.res_id]

            sliced_res_ids = [res_ids[i:i + self._batch_size] for i in range(0, len(res_ids), self._batch_size)]
            for res_ids in sliced_res_ids:
                all_mail_values = self.get_mail_values(cr, uid, wizard, res_ids, context=context)
                for res_id, mail_values in all_mail_values.iteritems():
                    if wizard.composition_mode == 'mass_mail':
                        self.pool['mail.mail'].create(cr, uid, mail_values, context=context)
                    else:
                        subtype = 'mail.mt_comment'
                        if context.get('mail_compose_log') or (wizard.composition_mode == 'mass_post' and not wizard.notify):  # log a note: subtype is False
                            subtype = False
                        if wizard.composition_mode == 'mass_post':
                            context = dict(context,
                                           mail_notify_force_send=False,  # do not send emails directly but use the queue instead
                                           mail_create_nosubscribe=True)  # add context key to avoid subscribing the author
                        active_model_pool.message_post(cr, uid, [res_id], type='comment', subtype=subtype, context=context, **mail_values)

        return {'type': 'ir.actions.act_window_close'}

    def get_mail_values(self, cr, uid, wizard, res_ids, context=None):
        """Generate the values that will be used by send_mail to create mail_messages
        or mail_mails. """
        results = dict.fromkeys(res_ids, False)
        rendered_values, default_recipients = {}, {}
        mass_mail_mode = wizard.composition_mode == 'mass_mail'

        # render all template-based value at once
        if mass_mail_mode and wizard.model:
            rendered_values = self.render_message_batch(cr, uid, wizard, res_ids, context=context)
        # compute alias-based reply-to in batch
        reply_to_value = dict.fromkeys(res_ids, None)
        if mass_mail_mode and wizard.same_thread:
            reply_to_value = self.pool['mail.thread'].message_get_reply_to(cr, uid, res_ids, default=wizard.email_from, context=dict(context, thread_model=wizard.model))

        for res_id in res_ids:
            # static wizard (mail.message) values
            mail_values = {
                'subject': wizard.subject,
                'body': wizard.body,
                'parent_id': wizard.parent_id and wizard.parent_id.id,
                'partner_ids': [partner.id for partner in wizard.partner_ids],
                'attachment_ids': [attach.id for attach in wizard.attachment_ids],
                'author_id': wizard.author_id.id,
                'email_from': wizard.email_from,
                'record_name': wizard.record_name,
            }
            # mass mailing: rendering override wizard static values
            if mass_mail_mode and wizard.model:
                # always keep a copy, reset record name (avoid browsing records)
                mail_values.update(notification=True, model=wizard.model, res_id=res_id, record_name=False)
                # auto deletion of mail_mail
                if 'mail_auto_delete' in context:
                    mail_values['auto_delete'] = context.get('mail_auto_delete')
                # rendered values using template
                email_dict = rendered_values[res_id]
                mail_values['partner_ids'] += email_dict.pop('partner_ids', [])
                mail_values.update(email_dict)
                if wizard.same_thread:
                    mail_values.pop('reply_to')
                    if reply_to_value.get(res_id):
                        mail_values['reply_to'] = reply_to_value[res_id]
                if not wizard.same_thread and not mail_values.get('reply_to'):
                    mail_values['reply_to'] = mail_values['email_from']
                # mail_mail values: body -> body_html, partner_ids -> recipient_ids
                mail_values['body_html'] = mail_values.get('body', '')
                mail_values['recipient_ids'] = [(4, id) for id in mail_values.pop('partner_ids', [])]

                # process attachments: should not be encoded before being processed by message_post / mail_mail create
                mail_values['attachments'] = [(name, base64.b64decode(enc_cont)) for name, enc_cont in email_dict.pop('attachments', list())]
                attachment_ids = []
                for attach_id in mail_values.pop('attachment_ids'):
                    new_attach_id = self.pool.get('ir.attachment').copy(cr, uid, attach_id, {'res_model': self._name, 'res_id': wizard.id}, context=context)
                    attachment_ids.append(new_attach_id)
                mail_values['attachment_ids'] = self.pool['mail.thread']._message_preprocess_attachments(
                    cr, uid, mail_values.pop('attachments', []),
                    attachment_ids, 'mail.message', 0, context=context)

            results[res_id] = mail_values
        return results

    #------------------------------------------------------
    # Template rendering
    #------------------------------------------------------

    def render_message_batch(self, cr, uid, wizard, res_ids, context=None):
        """Generate template-based values of wizard, for the document records given
        by res_ids. This method is meant to be inherited by email_template that
        will produce a more complete dictionary, using Jinja2 templates.

        Each template is generated for all res_ids, allowing to parse the template
        once, and render it multiple times. This is useful for mass mailing where
        template rendering represent a significant part of the process.

        Default recipients are also computed, based on mail_thread method
        message_get_default_recipients. This allows to ensure a mass mailing has
        always some recipients specified.

        :param browse wizard: current mail.compose.message browse record
        :param list res_ids: list of record ids

        :return dict results: for each res_id, the generated template values for
                              subject, body, email_from and reply_to
        """
        subjects = self.render_template_batch(cr, uid, wizard.subject, wizard.model, res_ids, context=context)
        bodies = self.render_template_batch(cr, uid, wizard.body, wizard.model, res_ids, context=context, post_process=True)
        emails_from = self.render_template_batch(cr, uid, wizard.email_from, wizard.model, res_ids, context=context)
        replies_to = self.render_template_batch(cr, uid, wizard.reply_to, wizard.model, res_ids, context=context)

        ctx = dict(context, thread_model=wizard.model)
        default_recipients = self.pool['mail.thread'].message_get_default_recipients(cr, uid, res_ids, context=ctx)

        results = dict.fromkeys(res_ids, False)
        for res_id in res_ids:
            results[res_id] = {
                'subject': subjects[res_id],
                'body': bodies[res_id],
                'email_from': emails_from[res_id],
                'reply_to': replies_to[res_id],
            }
            results[res_id].update(default_recipients.get(res_id, dict()))
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
