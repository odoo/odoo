# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import re

from odoo import _, api, fields, models, SUPERUSER_ID, tools
from odoo.tools import pycompat
from odoo.tools.safe_eval import safe_eval


# main mako-like expression pattern
EXPRESSION_PATTERN = re.compile('(\$\{.+?\})')


def _reopen(self, res_id, model, context=None):
    # save original model in context, because selecting the list of available
    # templates requires a model in context
    context = dict(context or {}, default_model=model)
    return {'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': res_id,
            'res_model': self._name,
            'target': 'new',
            'context': context,
            }


class MailComposer(models.TransientModel):
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

    @api.model
    def default_get(self, fields):
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
        result = super(MailComposer, self).default_get(fields)

        # v6.1 compatibility mode
        result['composition_mode'] = result.get('composition_mode', self._context.get('mail.compose.message.mode', 'comment'))
        result['model'] = result.get('model', self._context.get('active_model'))
        result['res_id'] = result.get('res_id', self._context.get('active_id'))
        result['parent_id'] = result.get('parent_id', self._context.get('message_id'))
        if 'no_auto_thread' not in result and (result['model'] not in self.env or not hasattr(self.env[result['model']], 'message_post')):
            result['no_auto_thread'] = True

        # default values according to composition mode - NOTE: reply is deprecated, fall back on comment
        if result['composition_mode'] == 'reply':
            result['composition_mode'] = 'comment'
        vals = {}
        if 'active_domain' in self._context:  # not context.get() because we want to keep global [] domains
            vals['active_domain'] = '%s' % self._context.get('active_domain')
        if result['composition_mode'] == 'comment':
            vals.update(self.get_record_data(result))

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
        if result['model'] == 'res.users' and result['res_id'] == self._uid:
            result['model'] = 'res.partner'
            result['res_id'] = self.env.user.partner_id.id

        if fields is not None:
            [result.pop(field, None) for field in list(result) if field not in fields]
        return result

    @api.model
    def _get_composition_mode_selection(self):
        return [('comment', 'Post on a document'),
                ('mass_mail', 'Email Mass Mailing'),
                ('mass_post', 'Post on Multiple Documents')]

    composition_mode = fields.Selection(selection=_get_composition_mode_selection, string='Composition mode', default='comment')
    partner_ids = fields.Many2many(
        'res.partner', 'mail_compose_message_res_partner_rel',
        'wizard_id', 'partner_id', 'Additional Contacts')
    use_active_domain = fields.Boolean('Use active domain')
    active_domain = fields.Text('Active domain', readonly=True)
    attachment_ids = fields.Many2many(
        'ir.attachment', 'mail_compose_message_ir_attachments_rel',
        'wizard_id', 'attachment_id', 'Attachments')
    is_log = fields.Boolean('Log an Internal Note',
                            help='Whether the message is an internal note (comment mode only)')
    subject = fields.Char(default=False)
    # mass mode options
    notify = fields.Boolean('Notify followers', help='Notify followers of the document (mass post only)')
    auto_delete = fields.Boolean('Delete Emails', help='Delete sent emails (mass mailing only)')
    auto_delete_message = fields.Boolean('Delete Message Copy', help='Do not keep a copy of the email in the document communication history (mass mailing only)')
    template_id = fields.Many2one(
        'mail.template', 'Use template', index=True,
        domain="[('model', '=', model)]")
    # mail_message updated fields
    message_type = fields.Selection(default="comment")
    subtype_id = fields.Many2one(default=lambda self: self.env['ir.model.data'].xmlid_to_res_id('mail.mt_comment'))

    @api.multi
    def check_access_rule(self, operation):
        """ Access rules of mail.compose.message:
            - create: if
                - model, no res_id, I create a message in mass mail mode
            - then: fall back on mail.message acces rules
        """
        # Author condition (CREATE (mass_mail))
        if operation == 'create' and self._uid != SUPERUSER_ID:
            # read mail_compose_message.ids to have their values
            message_values = {}
            self._cr.execute('SELECT DISTINCT id, model, res_id FROM "%s" WHERE id = ANY (%%s) AND res_id = 0' % self._table, (self.ids,))
            for mid, rmod, rid in self._cr.fetchall():
                message_values[mid] = {'model': rmod, 'res_id': rid}
            # remove from the set to check the ids that mail_compose_message accepts
            author_ids = [mid for mid, message in message_values.items()
                          if message.get('model') and not message.get('res_id')]
            self = self.browse(list(set(self.ids) - set(author_ids)))  # not sure slef = ...

        return super(MailComposer, self).check_access_rule(operation)

    @api.multi
    def _notify(self, **kwargs):
        """ Override specific notify method of mail.message, because we do
            not want that feature in the wizard. """
        return

    @api.model
    def get_record_data(self, values):
        """ Returns a defaults-like dict with initial values for the composition
        wizard when sending an email related a previous email (parent_id) or
        a document (model, res_id). This is based on previously computed default
        values. """
        result, subject = {}, False
        if values.get('parent_id'):
            parent = self.env['mail.message'].browse(values.get('parent_id'))
            result['record_name'] = parent.record_name,
            subject = tools.ustr(parent.subject or parent.record_name or '')
            if not values.get('model'):
                result['model'] = parent.model
            if not values.get('res_id'):
                result['res_id'] = parent.res_id
            partner_ids = values.get('partner_ids', list()) + [(4, id) for id in parent.partner_ids.ids]
            if self._context.get('is_private') and parent.author_id:  # check message is private then add author also in partner list.
                partner_ids += [(4, parent.author_id.id)]
            result['partner_ids'] = partner_ids
        elif values.get('model') and values.get('res_id'):
            doc_name_get = self.env[values.get('model')].browse(values.get('res_id')).name_get()
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
    # action buttons call with positionnal arguments only, so we need an intermediary function
    # to ensure the context is passed correctly
    @api.multi
    def action_send_mail(self):
        self.send_mail()
        return {'type': 'ir.actions.act_window_close', 'infos': 'mail_sent'}


    @api.multi
    def send_mail(self, auto_commit=False):
        """ Process the wizard content and proceed with sending the related
            email(s), rendering any template patterns on the fly if needed. """
        notif_layout = self._context.get('custom_layout')
        # Several custom layouts make use of the model description at rendering, e.g. in the
        # 'View <document>' button. Some models are used for different business concepts, such as
        # 'purchase.order' which is used for a RFQ and and PO. To avoid confusion, we must use a
        # different wording depending on the state of the object.
        # Therefore, we can set the description in the context from the beginning to avoid falling
        # back on the regular display_name retrieved in '_notify_prepare_template_context'.
        model_description = self._context.get('model_description')
        for wizard in self:
            # Duplicate attachments linked to the email.template.
            # Indeed, basic mail.compose.message wizard duplicates attachments in mass
            # mailing mode. But in 'single post' mode, attachments of an email template
            # also have to be duplicated to avoid changing their ownership.
            if wizard.attachment_ids and wizard.composition_mode != 'mass_mail' and wizard.template_id:
                new_attachment_ids = []
                for attachment in wizard.attachment_ids:
                    if attachment in wizard.template_id.attachment_ids:
                        new_attachment_ids.append(attachment.copy({'res_model': 'mail.compose.message', 'res_id': wizard.id}).id)
                    else:
                        new_attachment_ids.append(attachment.id)
                wizard.write({'attachment_ids': [(6, 0, new_attachment_ids)]})

            # Mass Mailing
            mass_mode = wizard.composition_mode in ('mass_mail', 'mass_post')

            Mail = self.env['mail.mail']
            ActiveModel = self.env[wizard.model] if wizard.model and hasattr(self.env[wizard.model], 'message_post') else self.env['mail.thread']
            if wizard.composition_mode == 'mass_post':
                # do not send emails directly but use the queue instead
                # add context key to avoid subscribing the author
                ActiveModel = ActiveModel.with_context(mail_notify_force_send=False, mail_create_nosubscribe=True)
            # wizard works in batch mode: [res_id] or active_ids or active_domain
            if mass_mode and wizard.use_active_domain and wizard.model:
                res_ids = self.env[wizard.model].search(safe_eval(wizard.active_domain)).ids
            elif mass_mode and wizard.model and self._context.get('active_ids'):
                res_ids = self._context['active_ids']
            else:
                res_ids = [wizard.res_id]

            batch_size = int(self.env['ir.config_parameter'].sudo().get_param('mail.batch_size')) or self._batch_size
            sliced_res_ids = [res_ids[i:i + batch_size] for i in range(0, len(res_ids), batch_size)]

            if wizard.composition_mode == 'mass_mail' or wizard.is_log or (wizard.composition_mode == 'mass_post' and not wizard.notify):  # log a note: subtype is False
                subtype_id = False
            elif wizard.subtype_id:
                subtype_id = wizard.subtype_id.id
            else:
                subtype_id = self.env['ir.model.data'].xmlid_to_res_id('mail.mt_comment')

            for res_ids in sliced_res_ids:
                batch_mails = Mail
                all_mail_values = wizard.get_mail_values(res_ids)
                for res_id, mail_values in all_mail_values.items():
                    if wizard.composition_mode == 'mass_mail':
                        batch_mails |= Mail.create(mail_values)
                    else:
                        post_params = dict(
                            message_type=wizard.message_type,
                            subtype_id=subtype_id,
                            notif_layout=notif_layout,
                            add_sign=not bool(wizard.template_id),
                            mail_auto_delete=wizard.template_id.auto_delete if wizard.template_id else False,
                            model_description=model_description,
                            **mail_values)
                        if ActiveModel._name == 'mail.thread' and wizard.model:
                            post_params['model'] = wizard.model
                        ActiveModel.browse(res_id).message_post(**post_params)

                if wizard.composition_mode == 'mass_mail':
                    batch_mails.send(auto_commit=auto_commit)

    @api.multi
    def get_mail_values(self, res_ids):
        """Generate the values that will be used by send_mail to create mail_messages
        or mail_mails. """
        self.ensure_one()
        results = dict.fromkeys(res_ids, False)
        rendered_values = {}
        mass_mail_mode = self.composition_mode == 'mass_mail'

        # render all template-based value at once
        if mass_mail_mode and self.model:
            rendered_values = self.render_message(res_ids)
        # compute alias-based reply-to in batch
        reply_to_value = dict.fromkeys(res_ids, None)
        if mass_mail_mode and not self.no_auto_thread:
            records = self.env[self.model].browse(res_ids)
            reply_to_value = self.env['mail.thread']._notify_get_reply_to_on_records(default=self.email_from, records=records)

        blacklisted_rec_ids = []
        if mass_mail_mode and hasattr(self.env[self.model], "_primary_email"):
            BL_sudo = self.env['mail.blacklist'].sudo()
            blacklist = set(BL_sudo.search([]).mapped('email'))
            if blacklist:
                [email_field] = self.env[self.model]._primary_email
                targets = self.env[self.model].browse(res_ids).read([email_field])
                # First extract email from recipient before comparing with blacklist
                for target in targets:
                    sanitized_email = self.env['mail.blacklist']._sanitize_email(target.get(email_field))
                    if sanitized_email and sanitized_email in blacklist:
                        blacklisted_rec_ids.append(target['id'])

        for res_id in res_ids:
            # static wizard (mail.message) values
            mail_values = {
                'subject': self.subject,
                'body': self.body or '',
                'parent_id': self.parent_id and self.parent_id.id,
                'partner_ids': [partner.id for partner in self.partner_ids],
                'attachment_ids': [attach.id for attach in self.attachment_ids],
                'author_id': self.author_id.id,
                'email_from': self.email_from,
                'record_name': self.record_name,
                'no_auto_thread': self.no_auto_thread,
                'mail_server_id': self.mail_server_id.id,
                'mail_activity_type_id': self.mail_activity_type_id.id,
            }

            # mass mailing: rendering override wizard static values
            if mass_mail_mode and self.model:
                mail_values.update(self.env['mail.thread']._notify_specific_email_values_on_records(False, records=self.env[self.model].browse(res_id)))
                # keep a copy unless specifically requested, reset record name (avoid browsing records)
                mail_values.update(notification=not self.auto_delete_message, model=self.model, res_id=res_id, record_name=False)
                # auto deletion of mail_mail
                if self.auto_delete or self.template_id.auto_delete:
                    mail_values['auto_delete'] = True
                # rendered values using template
                email_dict = rendered_values[res_id]
                mail_values['partner_ids'] += email_dict.pop('partner_ids', [])
                mail_values.update(email_dict)
                if not self.no_auto_thread:
                    mail_values.pop('reply_to')
                    if reply_to_value.get(res_id):
                        mail_values['reply_to'] = reply_to_value[res_id]
                if self.no_auto_thread and not mail_values.get('reply_to'):
                    mail_values['reply_to'] = mail_values['email_from']
                # mail_mail values: body -> body_html, partner_ids -> recipient_ids
                mail_values['body_html'] = mail_values.get('body', '')
                mail_values['recipient_ids'] = [(4, id) for id in mail_values.pop('partner_ids', [])]

                # process attachments: should not be encoded before being processed by message_post / mail_mail create
                mail_values['attachments'] = [(name, base64.b64decode(enc_cont)) for name, enc_cont in email_dict.pop('attachments', list())]
                attachment_ids = []
                for attach_id in mail_values.pop('attachment_ids'):
                    new_attach_id = self.env['ir.attachment'].browse(attach_id).copy({'res_model': self._name, 'res_id': self.id})
                    attachment_ids.append(new_attach_id.id)
                mail_values['attachment_ids'] = self.env['mail.thread']._message_post_process_attachments(
                    mail_values.pop('attachments', []),
                    attachment_ids,
                    {'model': 'mail.message', 'res_id': 0}
                )
                # Filter out the blacklisted records by setting the mail state to cancel -> Used for Mass Mailing stats
                if res_id in blacklisted_rec_ids:
                    mail_values['state'] = 'cancel'
                    # Do not post the mail into the recipient's chatter
                    mail_values['notification'] = False

            results[res_id] = mail_values
        return results

    #------------------------------------------------------
    # Template methods
    #------------------------------------------------------

    @api.multi
    @api.onchange('template_id')
    def onchange_template_id_wrapper(self):
        self.ensure_one()
        values = self.onchange_template_id(self.template_id.id, self.composition_mode, self.model, self.res_id)['value']
        for fname, value in values.items():
            setattr(self, fname, value)

    @api.multi
    def onchange_template_id(self, template_id, composition_mode, model, res_id):
        """ - mass_mailing: we cannot render, so return the template values
            - normal mode: return rendered values
            /!\ for x2many field, this onchange return command instead of ids
        """
        if template_id and composition_mode == 'mass_mail':
            template = self.env['mail.template'].browse(template_id)
            fields = ['subject', 'body_html', 'email_from', 'reply_to', 'mail_server_id']
            values = dict((field, getattr(template, field)) for field in fields if getattr(template, field))
            if template.attachment_ids:
                values['attachment_ids'] = [att.id for att in template.attachment_ids]
            if template.mail_server_id:
                values['mail_server_id'] = template.mail_server_id.id
            if template.user_signature and 'body_html' in values:
                signature = self.env.user.signature
                values['body_html'] = tools.append_content_to_html(values['body_html'], signature, plaintext=False)
        elif template_id:
            values = self.generate_email_for_composer(template_id, [res_id])[res_id]
            # transform attachments into attachment_ids; not attached to the document because this will
            # be done further in the posting process, allowing to clean database if email not send
            attachment_ids = []
            Attachment = self.env['ir.attachment']
            for attach_fname, attach_datas in values.pop('attachments', []):
                data_attach = {
                    'name': attach_fname,
                    'datas': attach_datas,
                    'datas_fname': attach_fname,
                    'res_model': 'mail.compose.message',
                    'res_id': 0,
                    'type': 'binary',  # override default_type from context, possibly meant for another model!
                }
                attachment_ids.append(Attachment.create(data_attach).id)
            if values.get('attachment_ids', []) or attachment_ids:
                values['attachment_ids'] = [(5,)] + values.get('attachment_ids', []) + attachment_ids
        else:
            default_values = self.with_context(default_composition_mode=composition_mode, default_model=model, default_res_id=res_id).default_get(['composition_mode', 'model', 'res_id', 'parent_id', 'partner_ids', 'subject', 'body', 'email_from', 'reply_to', 'attachment_ids', 'mail_server_id'])
            values = dict((key, default_values[key]) for key in ['subject', 'body', 'partner_ids', 'email_from', 'reply_to', 'attachment_ids', 'mail_server_id'] if key in default_values)

        if values.get('body_html'):
            values['body'] = values.pop('body_html')

        # This onchange should return command instead of ids for x2many field.
        # ORM handle the assignation of command list on new onchange (api.v8),
        # this force the complete replacement of x2many field with
        # command and is compatible with onchange api.v7
        values = self._convert_to_write(values)

        return {'value': values}

    @api.multi
    def save_as_template(self):
        """ hit save as template button: current form value will be a new
            template attached to the current document. """
        for record in self:
            model = self.env['ir.model']._get(record.model or 'mail.message')
            model_name = model.name or ''
            template_name = "%s: %s" % (model_name, tools.ustr(record.subject))
            values = {
                'name': template_name,
                'subject': record.subject or False,
                'body_html': record.body or False,
                'model_id': model.id or False,
                'attachment_ids': [(6, 0, [att.id for att in record.attachment_ids])],
            }
            template = self.env['mail.template'].create(values)
            # generate the saved template
            record.write({'template_id': template.id})
            record.onchange_template_id_wrapper()
            return _reopen(self, record.id, record.model, context=self._context)

    #------------------------------------------------------
    # Template rendering
    #------------------------------------------------------

    @api.multi
    def render_message(self, res_ids):
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
        self.ensure_one()
        multi_mode = True
        if isinstance(res_ids, pycompat.integer_types):
            multi_mode = False
            res_ids = [res_ids]

        subjects = self.env['mail.template']._render_template(self.subject, self.model, res_ids)
        bodies = self.env['mail.template']._render_template(self.body, self.model, res_ids, post_process=True)
        emails_from = self.env['mail.template']._render_template(self.email_from, self.model, res_ids)
        replies_to = self.env['mail.template']._render_template(self.reply_to, self.model, res_ids)
        default_recipients = {}
        if not self.partner_ids:
            default_recipients = self.env['mail.thread'].message_get_default_recipients(res_model=self.model, res_ids=res_ids)

        results = dict.fromkeys(res_ids, False)
        for res_id in res_ids:
            results[res_id] = {
                'subject': subjects[res_id],
                'body': bodies[res_id],
                'email_from': emails_from[res_id],
                'reply_to': replies_to[res_id],
            }
            results[res_id].update(default_recipients.get(res_id, dict()))

        # generate template-based values
        if self.template_id:
            template_values = self.generate_email_for_composer(
                self.template_id.id, res_ids,
                fields=['email_to', 'partner_to', 'email_cc', 'attachment_ids', 'mail_server_id'])
        else:
            template_values = {}

        for res_id in res_ids:
            if template_values.get(res_id):
                # recipients are managed by the template
                results[res_id].pop('partner_ids', None)
                results[res_id].pop('email_to', None)
                results[res_id].pop('email_cc', None)
                # remove attachments from template values as they should not be rendered
                template_values[res_id].pop('attachment_ids', None)
            else:
                template_values[res_id] = dict()
            # update template values by composer values
            template_values[res_id].update(results[res_id])

        return multi_mode and template_values or template_values[res_ids[0]]

    @api.model
    def generate_email_for_composer(self, template_id, res_ids, fields=None):
        """ Call email_template.generate_email(), get fields relevant for
            mail.compose.message, transform email_cc and email_to into partner_ids """
        multi_mode = True
        if isinstance(res_ids, pycompat.integer_types):
            multi_mode = False
            res_ids = [res_ids]

        if fields is None:
            fields = ['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc',  'reply_to', 'attachment_ids', 'mail_server_id']
        returned_fields = fields + ['partner_ids', 'attachments']
        values = dict.fromkeys(res_ids, False)

        template_values = self.env['mail.template'].with_context(tpl_partners_only=True).browse(template_id).generate_email(res_ids, fields=fields)
        for res_id in res_ids:
            res_id_values = dict((field, template_values[res_id][field]) for field in returned_fields if template_values[res_id].get(field))
            res_id_values['body'] = res_id_values.pop('body_html', '')
            values[res_id] = res_id_values

        return multi_mode and values or values[res_ids[0]]
