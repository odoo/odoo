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
        'attachment_ids': fields.many2many('ir.attachment',
            'mail_compose_message_ir_attachments_rel',
            'wizard_id', 'attachment_id', 'Attachments'),
        'filter_id': fields.many2one('ir.filters', 'Filters'),
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

    def _notify(self, cr, uid, newid, context=None):
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
        doc_name_get = self.pool.get(model).name_get(cr, uid, [res_id], context=context)
        if doc_name_get:
            record_name = doc_name_get[0][1]
        else:
            record_name = False
        return {'model': model, 'res_id': res_id, 'record_name': record_name}

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
        reply_subject = tools.ustr(message_data.subject or '')
        if not (reply_subject.startswith('Re:') or reply_subject.startswith(re_prefix)) and message_data.subject:
            reply_subject = "%s %s" % (re_prefix, reply_subject)
        # get partner_ids from original message
        partner_ids = [partner.id for partner in message_data.partner_ids] if message_data.partner_ids else []
        partner_ids += context.get('default_partner_ids', [])

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
        active_ids = context.get('active_ids')
        is_log = context.get('mail_compose_log', False)

        for wizard in self.browse(cr, uid, ids, context=context):
            mass_mail_mode = wizard.composition_mode == 'mass_mail'
            active_model_pool = self.pool.get(wizard.model if wizard.model else 'mail.thread')

            # wizard works in batch mode: [res_id] or active_ids
            res_ids = active_ids if mass_mail_mode and wizard.model and active_ids else [wizard.res_id]
            for res_id in res_ids:
                # default values, according to the wizard options
                post_values = {
                    'subject': wizard.subject,
                    'body': wizard.body,
                    'parent_id': wizard.parent_id and wizard.parent_id.id,
                    'partner_ids': [partner.id for partner in wizard.partner_ids],
                    'attachments': [(attach.datas_fname or attach.name, base64.b64decode(attach.datas)) for attach in wizard.attachment_ids],
                }
                # mass mailing: render and override default values
                if mass_mail_mode and wizard.model:
                    email_dict = self.render_message(cr, uid, wizard, res_id, context=context)
                    new_partner_ids = email_dict.pop('partner_ids', [])
                    post_values['partner_ids'] += new_partner_ids
                    new_attachments = email_dict.pop('attachments', [])
                    post_values['attachments'] += new_attachments
                    post_values.update(email_dict)
                # post the message
                subtype = 'mail.mt_comment'
                if is_log:  # log a note: subtype is False
                    subtype = False
                elif mass_mail_mode:  # mass mail: is a log pushed to recipients, author not added
                    subtype = False
                    context = dict(context, mail_create_nosubscribe=True)  # add context key to avoid subscribing the author
                msg_id = active_model_pool.message_post(cr, uid, [res_id], type='comment', subtype=subtype, context=context, **post_values)
                # mass_mailing: notify specific partners, because subtype was False, and no-one was notified
                if mass_mail_mode and post_values['partner_ids']:
                    self.pool.get('mail.notification')._notify(cr, uid, msg_id, post_values['partner_ids'], context=context)

        return {'type': 'ir.actions.act_window_close'}

    def render_message(self, cr, uid, wizard, res_id, context=None):
        """ Generate an email from the template for given (wizard.model, res_id)
            pair. This method is meant to be inherited by email_template that
            will produce a more complete dictionary. """
        return {
            'subject': self.render_template(cr, uid, wizard.subject, wizard.model, res_id, context),
            'body': self.render_template(cr, uid, wizard.body, wizard.model, res_id, context),
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
                'user': self.pool.get('res.users').browse(cr, uid, uid, context=context),
                'object': self.pool.get(model).browse(cr, uid, res_id, context=context),
                'context': dict(context),  # copy context to prevent side-effects of eval
                })
            return result and tools.ustr(result) or ''
        return template and EXPRESSION_PATTERN.sub(merge, template)
