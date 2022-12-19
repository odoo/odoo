# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import base64
import datetime
import logging

from odoo import _, api, fields, models, tools, Command
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import email_re

_logger = logging.getLogger(__name__)


def _reopen(self, res_id, model, context=None):
    # save original model in context, because selecting the list of available
    # templates requires a model in context
    context = dict(context or {}, default_model=model)
    return {'type': 'ir.actions.act_window',
            'view_mode': 'form',
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
    _inherit = 'mail.composer.mixin'
    _description = 'Email composition wizard'
    _log_access = True
    _batch_size = 500

    @api.model
    def default_get(self, fields_list):
        """ Handle composition mode and contextual computation, until moving
        to computed fields. Support active_model / active_id(s) as valid default
        values, as this comes from standard web client usage.

        Note that supporting active_ids through composer is still done, as we
        may have to give a huge list of IDs that won't fit into res_ids field.
        """
        # support subtype xmlid, like ``message_post``, when easier than using ``ref``
        if self.env.context.get('default_subtype_xmlid'):
            self = self.with_context(
                default_subtype_id=self.env['ir.model.data']._xmlid_to_res_id(
                    self.env.context['default_subtype_xmlid']
                )
            )
        # deprecated record context management
        if 'default_res_id' in self.env.context:
            raise ValueError(_("Deprecated usage of 'default_res_id', should use 'default_res_ids'."))

        result = super().default_get(fields_list)

        # author
        missing_author = 'author_id' in fields_list and 'author_id' not in result
        missing_email_from = 'email_from' in fields_list and 'email_from' not in result
        if missing_author or missing_email_from:
            author_id, email_from = self.env['mail.thread']._message_compute_author(result.get('author_id'), result.get('email_from'), raise_on_email=False)
            if missing_email_from:
                result['email_from'] = email_from
            if missing_author:
                result['author_id'] = author_id

        # record context management
        if 'model' in fields_list and 'model' not in result:
            result['model'] = self.env.context.get('active_model')
        if 'res_ids' in fields_list and 'res_ids' not in result:
            if self.env.context.get('active_ids'):
                active_res_ids = self._parse_res_ids(self.env.context['active_ids'])
                # beware, field is limited in storage, usage of active_ids in context still required
                if active_res_ids and len(active_res_ids) <= self._batch_size:
                    result['res_ids'] = self.env.context['active_ids']
            elif self.env.context.get('active_id'):
                result['res_ids'] = [self.env.context['active_id']]
            else:
                result['res_ids'] = False
        # record / parent based computation
        if result.get('composition_mode') == 'comment' and (set(fields_list) & {'model', 'res_ids', 'partner_ids', 'subject'}):
            result.update(self.get_record_data(result))

        # threading support check: 'update' requires to use message_update/post
        if 'reply_to_mode' in fields_list and 'reply_to_mode' not in result and result.get('model'):
            if result['model'] not in self.env or not hasattr(self.env[result['model']], 'message_post'):
                result['reply_to_mode'] = 'new'

        # when being in new mode, create_uid is not granted -> ACLs issue may arise
        if 'create_uid' in fields_list and 'create_uid' not in result:
            result['create_uid'] = self.env.uid

        # batch post mode by default use queues for notifications
        if 'force_send' in fields_list and 'force_send' not in result:
            result['force_send'] = (
                result.get('composition_mode') != 'comment' or
                (not result.get('res_domain') and
                len(self._parse_res_ids(result.get('res_ids') or [])) <= 1)
            )

        return {
            fname: result[fname]
            for fname in result if fname in fields_list
        }

    def _partner_ids_domain(self):
        return expression.OR([
            [('type', '!=', 'private')],
            [('id', 'in', self.env.context.get('default_partner_ids', []))],
        ])

    # content
    subject = fields.Char('Subject', compute=False)
    body = fields.Html(
        'Contents', render_engine='qweb', render_options={'post_process': True},
        compute=False, default='', sanitize_style=True)
    parent_id = fields.Many2one(
        'mail.message', 'Parent Message', ondelete='set null')
    template_id = fields.Many2one('mail.template', 'Use template', domain="[('model', '=', model)]")
    attachment_ids = fields.Many2many(
        'ir.attachment', 'mail_compose_message_ir_attachments_rel',
        'wizard_id', 'attachment_id', 'Attachments')
    email_layout_xmlid = fields.Char('Email Notification Layout', copy=False)
    email_add_signature = fields.Boolean(default=True)
    # origin
    email_from = fields.Char('From', help="Email address of the sender. This field is set when no matching partner is found and replaces the author_id field in the chatter.")
    author_id = fields.Many2one(
        'res.partner', 'Author',
        help="Author of the message. If not set, email_from may hold an email address that did not match any partner.")
    # composition
    composition_mode = fields.Selection(
        selection=[('comment', 'Post on a document'),
                   ('mass_mail', 'Email Mass Mailing')],
        string='Composition mode', default='comment')
    composition_batch = fields.Boolean(
        'Batch composition', compute='_compute_composition_batch')  # more than 1 record (raw source)
    model = fields.Char('Related Document Model')
    model_is_thread = fields.Boolean('Thread-Enabled', compute='_compute_model_is_thread')
    res_ids = fields.Text('Related Document IDs')
    res_domain = fields.Text('Active domain')
    res_domain_user_id = fields.Many2one(
        'res.users', string='Responsible',
        help='Used as context used to evaluate composer domain')
    record_name = fields.Char(
        'Record Name',
        compute='_compute_record_name', readonly=False, store=True)  # useful only in monorecord comment mode
    # characteristics
    message_type = fields.Selection([
        ('comment', 'Comment'),
        ('notification', 'System notification')],
        'Type', required=True, default='comment',
        help="Message type: email for email message, notification for system "
             "message, comment for other messages such as user replies")
    subtype_id = fields.Many2one(
        'mail.message.subtype', 'Subtype', ondelete='set null',
        default=lambda self: self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment'))
    subtype_is_log = fields.Boolean('Is a log', compute='_compute_subtype_is_log')
    mail_activity_type_id = fields.Many2one('mail.activity.type', 'Mail Activity Type', ondelete='set null')
    # destination
    reply_to = fields.Char('Reply To', help='Reply email address. Setting the reply_to bypasses the automatic thread creation.')
    reply_to_force_new = fields.Boolean(
        string='Considers answers as new thread',
        help='Manage answers as new incoming emails instead of replies going to the same thread.')
    reply_to_mode = fields.Selection([
        ('update', 'Store email and replies in the chatter of each record'),
        ('new', 'Collect replies on a specific email address')],
        string='Replies', compute='_compute_reply_to_mode', inverse='_inverse_reply_to_mode',
        help="Original Discussion: Answers go in the original document discussion thread. \n Another Email Address: Answers go to the email address mentioned in the tracking message-id instead of original document discussion thread. \n This has an impact on the generated message-id.")
    # recipients
    partner_ids = fields.Many2many(
        'res.partner', 'mail_compose_message_res_partner_rel',
        'wizard_id', 'partner_id', 'Additional Contacts',
        domain=_partner_ids_domain)
    # sending
    auto_delete = fields.Boolean(
        'Delete Emails',
        compute="_compute_auto_delete", readonly=False, store=True,
        help='This option permanently removes any track of email after it\'s been sent, including from the Technical menu in the Settings, in order to preserve storage space of your Odoo database.')
    auto_delete_keep_log = fields.Boolean(
        'Keep Message Copy',
        compute="_compute_auto_delete_keep_log", readonly=False, store=True,
        help='Keep a copy of the email content if emails are removed (mass mailing only)')
    force_send = fields.Boolean(
        'Send mailing or notifications directly')
    mail_server_id = fields.Many2one('ir.mail_server', 'Outgoing mail server')
    scheduled_date = fields.Char(
        'Scheduled Date',
        help="In comment mode: if set, postpone notifications sending. "
             "In mass mail mode: if sent, send emails after that date. "
             "This date is considered as being in UTC timezone.")
    use_exclusion_list = fields.Boolean('Check Exclusion List', default=True)

    @api.constrains('res_ids')
    def _check_res_ids(self):
        """ Check res_ids is a valid list of integers (or Falsy). """
        for composer in self:
            composer._evaluate_res_ids()

    @api.constrains('res_domain')
    def _check_res_domain(self):
        """ Check domain is a valid domain if set (otherwise it is considered
        as a Falsy leaf. """
        for composer in self:
            composer._evaluate_res_domain()

    @api.depends('res_domain', 'res_ids')
    def _compute_composition_batch(self):
        """ Determine if batch mode is activated:

          * using res_domain: always batch (even if result is singleton at a
            given time, it is user and time dependent, hence batch);
          * res_ids: if more than one item in the list (void and singleton are
            not batch);
        """
        for composer in self:
            if composer.res_domain:
                composer.composition_batch = True
                continue
            res_ids = composer._evaluate_res_ids()
            composer.composition_batch = len(res_ids) > 1 if res_ids else False

    @api.depends('model')
    def _compute_model_is_thread(self):
        """ Determine if model is thread enabled. """
        for composer in self:
            model = self.env['ir.model']._get(composer.model)
            composer.model_is_thread = model.is_mail_thread

    @api.depends('composition_mode', 'model', 'parent_id', 'res_domain', 'res_ids')
    def _compute_record_name(self):
        """ Computation is coming either from parent message, either from the
        record's display name in monorecord comment mode.

        In batch mode it makes no sense to compute a single record name. In
        email mode it is not used anyway. """
        toreset = self.filtered(
            lambda comp: comp.record_name
                and (comp.composition_mode != 'comment' or comp.composition_batch)
        )
        if toreset:
            toreset.record_name = False

        toupdate = self.filtered(
            lambda comp: not comp.record_name
                            and comp.composition_mode == 'comment'
                            and not comp.composition_batch
        )
        for composer in toupdate:
            if composer.parent_id.record_name:
                composer.record_name = composer.parent_id.record_name
                continue
            res_ids = composer._evaluate_res_ids()
            if composer.model and len(res_ids) == 1:
                composer.record_name = self.env[composer.model].browse(res_ids).display_name

    @api.depends('subtype_id')
    def _compute_subtype_is_log(self):
        """ In comment mode, tells whether the subtype is a note. Subtype has
        no use in email mode, and this field will be False. """
        note_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note')
        self.subtype_is_log = False
        for composer in self.filtered('subtype_id'):
            composer.subtype_is_log = composer.subtype_id.id == note_id

    @api.depends('reply_to_force_new')
    def _compute_reply_to_mode(self):
        for composer in self:
            composer.reply_to_mode = 'new' if composer.reply_to_force_new else 'update'

    def _inverse_reply_to_mode(self):
        for composer in self:
            composer.reply_to_force_new = composer.reply_to_mode == 'new'

    @api.depends('composition_mode', 'template_id')
    def _compute_auto_delete(self):
        """ Computation is coming either from template, either from composition
        mode. When having a template, its value is copied. Without template it
        is True in comment mode to remove notification emails by default. In
        email mode we keep emails (backward compatibility mode). """
        for composer in self:
            if composer.template_id:
                composer.auto_delete = composer.template_id.auto_delete
            else:
                composer.auto_delete = composer.composition_mode == 'comment'

    @api.depends('composition_mode', 'auto_delete')
    def _compute_auto_delete_keep_log(self):
        """ Keep logs is used only in email mode. It is used to keep the core
        message when unlinking sent emails. It allows to keep the message as
        a trace in the record's chatter. In other modes it has no use and
        can be set to False. When auto_delete is turned off it has no usage. """
        toreset = self.filtered(
            lambda comp: comp.composition_mode != 'mass_mail' or
                            not comp.auto_delete
        )
        toreset.auto_delete_keep_log = False
        (self - toreset).auto_delete_keep_log = True

    # Overrides of mail.render.mixin
    @api.depends('model')
    def _compute_render_model(self):
        for composer in self:
            composer.render_model = composer.model

    def _compute_can_edit_body(self):
        """Can edit the body if we are not in "mass_mail" mode because the template is
        rendered before it's modified.
        """
        non_mass_mail = self.filtered(lambda m: m.composition_mode != 'mass_mail')
        non_mass_mail.can_edit_body = True
        super(MailComposer, self - non_mass_mail)._compute_can_edit_body()

    # Onchanges

    @api.onchange('template_id')
    def _onchange_template_id_wrapper(self):
        self.ensure_one()
        values = self._onchange_template_id(
            self.template_id.id,
            self.composition_mode,
            self.model,
            self._evaluate_res_ids(),
            self.res_domain,
        )['value']
        for fname, value in values.items():
            setattr(self, fname, value)

    def _onchange_template_id(self, template_id, composition_mode, model, res_ids, res_domain=None):
        """ Perform the onchange.

          * mass_mailing or comment in batch: we cannot render, so return the
            template values
          * normal mode: return rendered values
            -> for x2many field, this onchange return command instead of ids
        """
        if template_id and (composition_mode == 'mass_mail' or res_domain or len(res_ids) > 1):
            # copy raw template values (not rendered due to mass mode)
            template = self.env['mail.template'].browse(template_id)
            values = dict(
                (field, template[field])
                for field in ('email_from',
                              'reply_to',
                              'scheduled_date',
                              'subject',
                             )
                if template[field]
            )
            if template.attachment_ids:
                values['attachment_ids'] = [att.id for att in template.attachment_ids]
            if template.mail_server_id:
                values['mail_server_id'] = template.mail_server_id.id
            if not tools.is_html_empty(template.body_html):
                values['body'] = template.body_html
        elif template_id and len(res_ids) <= 1:
            # render template (mono record, comment mode) and set it as composer values
            # trick to evaluate qweb even when having no records
            template_res_ids = res_ids if res_ids else [0]
            values = self._generate_template_for_composer(
                self.env['mail.template'].browse(template_id),
                template_res_ids,
                ('attachment_ids',
                 'body_html',
                 'email_cc',
                 'email_from',
                 'email_to',
                 'mail_server_id',
                 'partner_ids',
                 'reply_to',
                 'report_template_ids',
                 'scheduled_date',
                 'subject',
                )
            )[template_res_ids[0]]
            # transform attachments into attachment_ids; not attached to the document because this will
            # be done further in the posting process, allowing to clean database if email not send
            attachment_ids = []
            Attachment = self.env['ir.attachment']
            for attach_fname, attach_datas in values.pop('attachments', []):
                data_attach = {
                    'name': attach_fname,
                    'datas': attach_datas,
                    'res_model': 'mail.compose.message',
                    'res_id': 0,
                    'type': 'binary',  # override default_type from context, possibly meant for another model!
                }
                attachment_ids.append(Attachment.create(data_attach).id)
            if values.get('attachment_ids', []) or attachment_ids:
                values['attachment_ids'] = [Command.set(values.get('attachment_ids', []) + attachment_ids)]
        else:
            default_values = self.with_context(
                default_composition_mode=composition_mode,
                default_model=model,
                default_res_ids=res_ids
            ).default_get(['attachment_ids',
                           'body',
                           'composition_mode',
                           'email_from',
                           'mail_server_id',
                           'model',
                           'parent_id',
                           'partner_ids',
                           'reply_to',
                           'res_ids',
                           'scheduled_date',
                           'subject',
                          ])
            values = dict(
                (key, default_values[key])
                for key in ('attachment_ids',
                            'body',
                            'email_from',
                            'mail_server_id',
                            'partner_ids',
                            'reply_to',
                            'scheduled_date',
                            'subject',
                           ) if key in default_values)

        # This onchange should return command instead of ids for x2many field.
        values = self._convert_to_write(values)

        return {'value': values}

    @api.model
    def get_record_data(self, values):
        """ Returns a defaults-like dict with initial values for the composition
        wizard when sending an email related a previous email (parent_id) or
        a document (model, res_id). This is based on previously computed default
        values. """
        result, subject = {}, False
        model = values.get('model')
        res_ids = self._parse_res_ids(values['res_ids']) if values.get('res_ids') else []
        if values.get('parent_id'):
            parent = self.env['mail.message'].browse(values.get('parent_id'))
            if not model:
                model = parent.model
                result['model'] = model
            if not res_ids:
                res_ids = [parent.res_id]
                result['res_ids'] = res_ids
            result['partner_ids'] = values.get('partner_ids', list()) + parent.partner_ids.ids
            subject = tools.ustr(parent.subject or '')
            if not subject and model and res_ids and len(res_ids) == 1:
                record = self.env[model].browse(res_ids[0])
                if not subject:
                    subject = record._message_compute_subject()
        elif model and len(res_ids) == 1:
            record = self.env[model].browse(res_ids[0])
            subject = record._message_compute_subject()

        if values.get('parent_id') or len(res_ids) == 1:  # to be cleanup when moving to computed fields
            result['subject'] = subject

        return result

    # ------------------------------------------------------------
    # CRUD / ORM
    # ------------------------------------------------------------

    @api.autovacuum
    def _gc_lost_attachments(self):
        """ Garbage collect lost mail attachments. Those are attachments
            - linked to res_model 'mail.compose.message', the composer wizard
            - with res_id 0, because they were created outside of an existing
                wizard (typically user input through Chatter or reports
                created on-the-fly by the templates)
            - unused since at least one day (create_date and write_date)
        """
        limit_date = fields.Datetime.subtract(fields.Datetime.now(), days=1)
        self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', '=', 0),
            ('create_date', '<', limit_date),
            ('write_date', '<', limit_date)]
        ).unlink()

    # ------------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------------

    def action_send_mail(self):
        """ Used for action button that do not accept arguments. """
        self._action_send_mail(auto_commit=False)
        return {'type': 'ir.actions.act_window_close'}

    def _action_send_mail(self, auto_commit=False):
        """ Process the wizard content and proceed with sending the related
            email(s), rendering any template patterns on the fly if needed.

        :return tuple: (
            result_mails_su: in mass mode, sent emails (as sudo),
            result_messages: in comment mode, posted messages
        )
        """
        result_mails_su, result_messages = self.env['mail.mail'].sudo(), self.env['mail.message']

        for wizard in self:
            if wizard.res_domain:
                search_domain = wizard._evaluate_res_domain()
                search_user = wizard.res_domain_user_id or self.env.user
                res_ids = self.env[wizard.model].with_user(search_user).search(search_domain).ids
            else:
                res_ids = wizard._evaluate_res_ids()
            # in comment mode: raise here as anyway message_post will raise.
            if not res_ids and wizard.composition_mode == 'comment':
                raise ValueError(
                    _('Mail composer in comment mode should run on at least one record. No records found (model %(model_name)s).',
                      model_name=wizard.model)
                )

            if wizard.composition_mode == 'mass_mail':
                result_mails_su += wizard._action_send_mail_mass_mail(res_ids, auto_commit=auto_commit)
            else:
                result_messages += wizard._action_send_mail_comment(res_ids)

        return result_mails_su, result_messages

    def _action_send_mail_comment(self, res_ids):
        """ Send in comment mode. It calls message_post on model, or the generic
        implementation of it if not available (as message_notify). """
        self.ensure_one()
        post_values_all = self._prepare_mail_values(res_ids)
        ActiveModel = self.env[self.model] if self.model and hasattr(self.env[self.model], 'message_post') else self.env['mail.thread']
        if self.composition_batch:
            # add context key to avoid subscribing the author
            ActiveModel = ActiveModel.with_context(
                mail_create_nosubscribe=True,
            )

        messages = self.env['mail.message']
        for res_id, post_values in post_values_all.items():
            if ActiveModel._name == 'mail.thread':
                post_values.pop('message_type')  # forced to user_notification
                post_values.pop('parent_id', False)  # not supported in notify
                if self.model:
                    post_values['model'] = self.model
                    post_values['res_id'] = res_id
                message = ActiveModel.message_notify(**post_values)
                if not message:
                    # if message_notify returns an empty record set, no recipients where found.
                    raise UserError(_("No recipient found."))
                messages += message
            else:
                messages += ActiveModel.browse(res_id).message_post(**post_values)
        return messages

    def _action_send_mail_mass_mail(self, res_ids, auto_commit=False):
        """ Send in mass mail mode. Mails are sudo-ed, as when going through
        _prepare_mail_values standard access rights on related records will be
        checked when browsing them to compute mail values. If people have
        access to the records they have rights to create lots of emails in
        sudo as it is considered as a technical model. """
        mails_sudo = self.env['mail.mail'].sudo()

        batch_size = int(self.env['ir.config_parameter'].sudo().get_param('mail.batch_size')) or self._batch_size
        sliced_res_ids = [res_ids[i:i + batch_size] for i in range(0, len(res_ids), batch_size)]

        for res_ids_iter in sliced_res_ids:
            mail_values_all = self._prepare_mail_values(res_ids_iter)

            iter_mails_sudo = self.env['mail.mail'].sudo()
            for _res_id, mail_values in mail_values_all.items():
                iter_mails_sudo += mails_sudo.create(mail_values)
            mails_sudo += iter_mails_sudo

            records = self.env[self.model].browse(res_ids_iter) if self.model and hasattr(self.env[self.model], 'message_post') else False
            if records:
                records._message_mail_after_hook(iter_mails_sudo)

            # as 'send' does not filter out scheduled mails (only 'process_email_queue'
            # does) we need to do it manually
            if not self.force_send:
                continue
            iter_mails_sudo_tosend = iter_mails_sudo.filtered(
                lambda mail: (
                    not mail.scheduled_date or
                    mail.scheduled_date <= datetime.datetime.utcnow()
                )
            )
            if iter_mails_sudo_tosend:
                iter_mails_sudo_tosend.send(auto_commit=auto_commit)

        return mails_sudo

    def action_save_as_template(self):
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
                'use_default_to': True,
            }
            template = self.env['mail.template'].create(values)

            if record.attachment_ids:
                attachments = self.env['ir.attachment'].sudo().browse(record.attachment_ids.ids).filtered(
                    lambda a: a.res_model == 'mail.compose.message' and a.create_uid.id == self._uid)
                if attachments:
                    attachments.write({'res_model': template._name, 'res_id': template.id})
                template.attachment_ids |= record.attachment_ids

            # generate the saved template
            record.write({'template_id': template.id})
            record._onchange_template_id_wrapper()
            return _reopen(self, record.id, record.model, context=self.env.context)

    # ------------------------------------------------------------
    # RENDERING / VALUES GENERATION
    # ------------------------------------------------------------

    def _prepare_mail_values(self, res_ids):
        """Generate the values that will be used by send_mail to create either
         mail_messages or mail_mails depending on composition mode.

        Some summarized information on generation: mail versus message fields
        (or both), and static (never rendered) versus dynamic (raw or rendered).

        MAIL
            STA - 'auto_delete',
            DYN - 'body_html',
            STA - 'force_send',  (notify parameter)
            STA - 'model',
            DYN - 'recipient_ids',  (from partner_ids)
            DYN - 'res_id',
            STA - 'is_notification',

        MESSAGE
            DYN - 'body',
            STA - 'email_add_signature',
            STA - 'email_layout_xmlid',

        BOTH
            DYN - 'attachment_ids',
            STA - 'author_id',  (to improve with template)
            DYN - 'email_from',
            STA - 'mail_activity_type_id',
            STA - 'mail_server_id',
            STA - 'message_type',
            STA - 'parent_id',
            DYN - 'partner_ids',
            STA - 'record_name',
            DYN - 'reply_to',
            STA - 'reply_to_force_new',
            DYN - 'scheduled_date',
            DYN - 'subject',
            STA - 'subtype_id',

        :param list res_ids: list of record IDs on which composer runs;

        :return dict: for each res_id, values to create the mail.mail or to
          give to message_post, depending on composition mode;
        """
        self.ensure_one()
        email_mode = self.composition_mode == 'mass_mail'
        rendering_mode = email_mode or self.composition_batch

        # values that do not depend on rendering mode
        base_values = self._prepare_mail_values_static()

        additional_values_all = {}
        # rendered based on raw content (wizard or template)
        if rendering_mode and self.model:
            additional_values_all = self._prepare_mail_values_dynamic(res_ids)
        # wizard content already rendered
        elif not rendering_mode:
            additional_values_all = self._prepare_mail_values_rendered(res_ids)

        mail_values_all = {
            res_id: dict(
                base_values,
                **additional_values_all.get(res_id, {})
            )
            for res_id in res_ids
        }

        if email_mode:
            mail_values_all = self._process_mail_values_state(mail_values_all)
        return mail_values_all

    def _prepare_mail_values_static(self):
        """Prepare values always valid, not rendered or dynamic whatever the
        composition mode and related records.

        :return dict: a dict of (field name, value) to be used to populate
          values for each res_id in '_prepare_mail_values';
        """
        self.ensure_one()
        email_mode = self.composition_mode == 'mass_mail'

        if email_mode:
            subtype_id = False
        elif self.subtype_id:
            subtype_id = self.subtype_id.id
        else:
            subtype_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment')

        values = {
            'author_id': self.author_id.id,
            'mail_activity_type_id': self.mail_activity_type_id.id,
            'mail_server_id': self.mail_server_id.id,
            'message_type': 'email' if email_mode else self.message_type,
            'parent_id': self.parent_id.id,
            'record_name': False if email_mode else self.record_name,
            'reply_to_force_new': self.reply_to_force_new,
            'subtype_id': subtype_id,
        }
        # specific to mass mailing mode
        if email_mode:
            values.update(
                auto_delete=self.auto_delete,
                is_notification=self.auto_delete_keep_log,
                model=self.model,
            )
        # specific to post mode
        else:
            # Several custom layouts make use of the model description at rendering, e.g. in the
            # 'View <document>' button. Some models are used for different business concepts, such as
            # 'purchase.order' which is used for a RFQ and and PO. To avoid confusion, we must use a
            # different wording depending on the state of the object.
            # Therefore, we can set the description in the context from the beginning to avoid falling
            # back on the regular display_name retrieved in ``_notify_by_email_prepare_rendering_context()``.
            model_description = self.env.context.get('model_description')
            values.update(
                email_add_signature=not bool(self.template_id) and self.email_add_signature,
                email_layout_xmlid=self.email_layout_xmlid,
                force_send=self.force_send,
                mail_auto_delete=self.auto_delete,
                model_description=model_description,
            )
        return values

    def _prepare_mail_values_dynamic(self, res_ids):
        """Generate values based on composer content as well as its template
        based on records given by res_ids.

        Part of the advanced rendering is delegated to template, notably
        recipients or attachments dynamic generation. See sub methods for
        more details.

        :param list res_ids: list of record IDs on which composer runs;

        :return dict results: for each res_id, the generated values used to
          populate in '_prepare_mail_values';
        """
        self.ensure_one()
        RecordsModel = self.env[self.model].with_prefetch(res_ids)
        email_mode = self.composition_mode == 'mass_mail'

        subjects = self._render_field('subject', res_ids)
        bodies = self._render_field(
            'body', res_ids,
            # We want to preserve comments in emails so as to keep mso conditionals
            options={'preserve_comments': email_mode},
        )
        emails_from = self._render_field('email_from', res_ids)

        mail_values_all = {
            res_id: {
                'body': bodies[res_id],  # should be void
                'email_from': emails_from[res_id],
                'scheduled_date': False,
                'subject': subjects[res_id],
                # some fields are specific to mail or message
                **(
                    {
                        'body_html': bodies[res_id],
                        'res_id': res_id,
                    } if email_mode else {}),
            }
            for res_id in res_ids
        }

        # generate template-based values
        if self.template_id:
            template_values = self._generate_template_for_composer(
                self.template_id,
                res_ids,
                ('attachment_ids',
                 'email_to',
                 'email_cc',
                 'mail_server_id',
                 'partner_ids',
                 'report_template_ids',
                 'scheduled_date',
                )
            )
            for res_id in res_ids:
                # remove attachments from template values as they should not be rendered
                template_values[res_id].pop('attachment_ids', None)
                mail_values_all[res_id].update(template_values[res_id])

        # Handle recipients. Without template, if no partner_ids is given, update
        # recipients using default recipients to be sure to notify someone
        if not self.template_id and not self.partner_ids:
            default_recipients = RecordsModel.browse(res_ids)._message_get_default_recipients()
            for res_id in res_ids:
                mail_values_all[res_id].update(
                    default_recipients.get(res_id, {})
                )

        # Handle reply-to. In update mode (force_new False), reply-to value is
        # computed from the records (to have their alias). In new mode, reply-to
        # is coming from reply_to field to render.
        if not self.reply_to_force_new:
            # compute alias-based reply-to in batch
            reply_to_values = RecordsModel.browse(res_ids)._notify_get_reply_to(default=False)
        if self.reply_to_force_new:
            reply_to_values = self._render_field('reply_to', res_ids)

        # Handle per-record update
        for res_id, mail_values in mail_values_all.items():
            record = RecordsModel.browse(res_id)

            # attachments. Copy attachment_ids (each has its own copies), and decode
            # attachments as required by _process_attachments_for_post
            attachment_ids = [
                attachment.copy({'res_model': self._name, 'res_id': self.id}).id
                for attachment in self.attachment_ids
            ]
            attachment_ids.reverse()
            decoded_attachments = [
                (name, base64.b64decode(enc_cont))
                for name, enc_cont in mail_values.pop('attachments', [])
            ]
            # email_mode: prepare processed attachments as commands for mail.mail
            if email_mode:
                mail_values['attachment_ids'] = record._process_attachments_for_post(
                    decoded_attachments,
                    attachment_ids,
                    {'model': 'mail.message', 'res_id': 0}
                )['attachment_ids']
            # comment mode: prepare attachments as a list of IDs, to be processed by MailThread
            else:
                mail_values['attachments'] = decoded_attachments
                mail_values['attachment_ids'] = attachment_ids

            # headers
            if email_mode:
                mail_values['headers'] = repr(record._notify_by_email_get_headers())

            # recipients: transform partner_ids (field used in mail_message) into
            # recipient_ids, used by mail_mail
            if email_mode:
                recipient_ids_all = mail_values.pop('partner_ids', []) + self.partner_ids.ids
                mail_values['recipient_ids'] = [(4, pid) for pid in recipient_ids_all]

            # when having no specific reply_to -> fetch rendered email_from
            if email_mode:
                reply_to = reply_to_values.get(res_id)
                if not reply_to:
                    reply_to = mail_values.get('email_from', False)
                mail_values['reply_to'] = reply_to

        return mail_values_all

    def _prepare_mail_values_rendered(self, res_ids):
        """Generate values that are already rendered. This is used mainly in
        monorecord mode, when the wizard contains value already generated
        (e.g. "Send by email" on a sale order, in form view).

        :param list res_ids: list of record IDs on which composer runs;

        :return dict results: for each res_id, the generated values used to
          populate in '_prepare_mail_values';
        """
        self.ensure_one()

        # Duplicate attachments linked to the email.template. Indeed, composer
        # duplicates attachments in mass mode. But in 'rendered' mode attachments
        # may come from an email template (same IDs). They also have to be
        # duplicated to avoid changing their ownership.
        if self.composition_mode == 'comment' and self.template_id and self.attachment_ids:
            new_attachment_ids = []
            for attachment in self.attachment_ids:
                if attachment in self.template_id.attachment_ids:
                    new_attachment_ids.append(attachment.copy({
                        'res_model': 'mail.compose.message',
                        'res_id': self.id,
                    }).id)
                else:
                    new_attachment_ids.append(attachment.id)
            new_attachment_ids.reverse()
            self.write({'attachment_ids': [Command.set(new_attachment_ids)]})

        return {
            res_id: {
                'attachment_ids': [attach.id for attach in self.attachment_ids],
                'body': self.body or '',
                'email_from': self.email_from,
                'partner_ids': self.partner_ids.ids,
                'scheduled_date': self.scheduled_date,
                'subject': self.subject or '',
            }
            for res_id in res_ids
        }

    def _process_mail_values_state(self, mail_values_dict):
        """ When being in mass mailing, avoid sending emails to void or invalid
        emails. For that purpose a processing of generated values allows to
        give a state and a failure type to mail.mail records that will be
        created at sending time.

        :param dict mail_values_dict: as generated by '_prepare_mail_values';

        :return: updated mail_values_dict
        """
        recipients_info = self._get_recipients_data(mail_values_dict)
        blacklist_ids = self._get_blacklist_record_ids(mail_values_dict)
        optout_emails = self._get_optout_emails(mail_values_dict)
        done_emails = self._get_done_emails(mail_values_dict)
        # in case of an invoice e.g.
        mailing_document_based = self.env.context.get('mailing_document_based')

        for record_id, mail_values in mail_values_dict.items():
            recipients = recipients_info[record_id]
            # when having more than 1 recipient: we cannot really decide when a single
            # email is linked to several to -> skip that part. Mass mailing should
            # anyway always have a single recipient per record as this is default behavior.
            if len(recipients['mail_to']) > 1:
                continue

            mail_to = recipients['mail_to'][0] if recipients['mail_to'] else ''
            mail_to_normalized = recipients['mail_to_normalized'][0] if recipients['mail_to_normalized'] else ''

            # prevent sending to blocked addresses that were included by mistake
            # blacklisted or optout or duplicate -> cancel
            if record_id in blacklist_ids:
                mail_values['state'] = 'cancel'
                mail_values['failure_type'] = 'mail_bl'
                # Do not post the mail into the recipient's chatter
                mail_values['is_notification'] = False
            elif optout_emails and mail_to in optout_emails:
                mail_values['state'] = 'cancel'
                mail_values['failure_type'] = 'mail_optout'
            elif done_emails and mail_to in done_emails and not mailing_document_based:
                mail_values['state'] = 'cancel'
                mail_values['failure_type'] = 'mail_dup'
            # void of falsy values -> error
            elif not mail_to:
                mail_values['state'] = 'cancel'
                mail_values['failure_type'] = 'mail_email_missing'
            elif not mail_to_normalized or not email_re.findall(mail_to):
                mail_values['state'] = 'cancel'
                mail_values['failure_type'] = 'mail_email_invalid'
            elif done_emails is not None and not mailing_document_based:
                done_emails.append(mail_to)

        return mail_values_dict

    def _generate_template_for_composer(self, template, res_ids, render_fields,
                                        find_or_create_partners=True):
        """ Generate values based on template and relevant values for the
        mail.compose.message wizard.

        :param record template: a mail template, as during onchange mode it
          may not be set on self (to remove when removing the onchange);
        :param list res_ids: list of record IDs on which template is rendered;
        :param list render_fields: list of fields to render on template;
        :param boolean find_or_create_partners: transform emails into partners
          (see ``Template._generate_template_recipients``);

        :returns: a dict containing all asked fields for each record ID given by
          res_ids. Note that

          * 'body' comes from template 'body_html' generation;
          * 'attachments' is an additional key coming with 'attachment_ids' due
            to report generation (in the format [(report_name, data)] where data
            is base64 encoded);
          * 'partner_ids' is returned due to recipients generation that gives
            partner ids coming from default computation as well as from email
            to partner convert (see ``find_or_create_partners``);
        """
        self.ensure_one()

        # some fields behave / are named differently on template model
        mapping = {
            'attachments': 'report_template_ids',
            'body': 'body_html',
            'partner_ids': 'partner_to',
        }
        template_fields = {mapping.get(fname, fname) for fname in render_fields}
        template_values = template._generate_template(
            res_ids,
            template_fields,
            find_or_create_partners=True
        )

        exclusion_list = ('email_cc', 'email_to') if find_or_create_partners else ()
        mapping = {'body_html': 'body'}
        render_results = {}
        for res_id in res_ids:
            render_results[res_id] = {
                mapping.get(fname, fname): value
                for fname, value in template_values[res_id].items()
                if fname not in exclusion_list and value
            }

        return render_results

    # ----------------------------------------------------------------------
    # EMAIL MANAGEMENT
    # ---------------------------------------------------------------------

    def _get_blacklist_record_ids(self, mail_values_dict):
        blacklisted_rec_ids = set()
        if not self.use_exclusion_list:
            return blacklisted_rec_ids
        if self.composition_mode == 'mass_mail' and issubclass(type(self.env[self.model]), self.pool['mail.thread.blacklist']):
            self.env['mail.blacklist'].flush_model(['email', 'active'])
            self._cr.execute("SELECT email FROM mail_blacklist WHERE active=true")
            blacklist = {x[0] for x in self._cr.fetchall()}
            if blacklist:
                targets = self.env[self.model].browse(mail_values_dict.keys()).read(['email_normalized'])
                # First extract email from recipient before comparing with blacklist
                blacklisted_rec_ids.update(target['id'] for target in targets
                                           if target['email_normalized'] in blacklist)
        return blacklisted_rec_ids

    def _get_done_emails(self, mail_values_dict):
        return []

    def _get_optout_emails(self, mail_values_dict):
        return []

    def _get_recipients_data(self, mail_values_dict):
        # Preprocess res.partners to batch-fetch from db if recipient_ids is present
        # it means they are partners (the only object to fill get_default_recipient this way)
        recipient_pids = [
            recipient_command[1]
            for mail_values in mail_values_dict.values()
            # recipient_ids is a list of x2m command tuples at this point
            for recipient_command in mail_values.get('recipient_ids') or []
            if recipient_command[1]
        ]
        recipient_emails = {
            p.id: p.email
            for p in self.env['res.partner'].browse(set(recipient_pids))
        } if recipient_pids else {}

        recipients_info = {}
        for record_id, mail_values in mail_values_dict.items():
            mail_to = []
            if mail_values.get('email_to'):
                mail_to += email_re.findall(mail_values['email_to'])
                # if unrecognized email in email_to -> keep it as used for further processing
                if not mail_to:
                    mail_to.append(mail_values['email_to'])
            # add email from recipients (res.partner)
            mail_to += [
                recipient_emails[recipient_command[1]]
                for recipient_command in mail_values.get('recipient_ids') or []
                if recipient_command[1]
            ]
            mail_to = list(set(mail_to))
            recipients_info[record_id] = {
                'mail_to': mail_to,
                'mail_to_normalized': [
                    tools.email_normalize(mail)
                    for mail in mail_to
                    if tools.email_normalize(mail)
                ]
            }
        return recipients_info

    # ----------------------------------------------------------------------
    # MISC UTILS
    # ----------------------------------------------------------------------

    def _evaluate_res_domain(self):
        """ Parse composer domain, which can be: an already valid list or
        tuple (generally in code), a list or tuple as a string (coming from
        actions). Void strings are considered as a falsy domain.

        :return: an Odoo domain (list of leaves) """
        self.ensure_one()
        if isinstance(self.res_domain, (str, bool)) and not self.res_domain:
            return expression.FALSE_DOMAIN
        try:
            domain = self.res_domain
            if isinstance(self.res_domain, str):
                domain = ast.literal_eval(domain)

            expression.expression(
                domain,
                self.env[self.model],
            )
        except (ValueError, AssertionError) as e:
            raise ValidationError(
                _("Invalid domain %(domain)r (type %(domain_type)s)",
                    domain=self.res_domain,
                    domain_type=type(self.res_domain))
            ) from e

        return domain

    def _evaluate_res_ids(self):
        """ Parse composer res_ids, which can be: an already valid list or
        tuple (generally in code), a list or tuple as a string (coming from
        actions). Void strings / missing values are evaluated as an empty list.

        Note that 'active_ids' context key is supported at this point as mailing
        on big ID list would create issues if stored in database.

        Another context key 'composer_force_res_ids' is temporarily supported
        to ease support of accounting wizard, while waiting to implement a
        proper solution to language management.

        :return: a list of IDs (empty list in case of falsy strings)"""
        self.ensure_one()
        return self._parse_res_ids(
            self.env.context.get('composer_force_res_ids') or
            self.res_ids or
            self.env.context.get('active_ids')
        ) or []

    @api.model
    def _parse_res_ids(self, res_ids):
        if tools.is_list_of(res_ids, int) or not res_ids:
            return res_ids
        error_msg = _("Invalid res_ids %(res_ids_str)s (type %(res_ids_type)s)",
                      res_ids_str=res_ids,
                      res_ids_type=type(res_ids))
        try:
            res_ids = ast.literal_eval(res_ids)
        except Exception as e:
            raise ValidationError(error_msg) from e
        if not tools.is_list_of(res_ids, int):
            raise ValidationError(error_msg)
        return res_ids
