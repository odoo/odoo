# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import base64
import datetime
import logging

from odoo import _, api, fields, models, tools, Command
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import is_html_empty
from odoo.addons.mail.tools.parser import parse_res_ids


def _reopen(self, res_id, model, context=None):
    # save original model in context, because selecting the list of available
    # templates requires a model in context
    context = dict(context or {}, default_model=model)
    return {'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
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
        - 'comment': post on a record.
        - 'mass_mail': wizard in mass mailing mode where the mail details can
            contain template placeholders that will be merged with actual data
            before being sent to each recipient.
    """
    _name = 'mail.compose.message'
    _inherit = 'mail.composer.mixin'
    _description = 'Email composition wizard'
    _log_access = True
    _batch_size = 50

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

        # when being in new mode, create_uid is not granted -> ACLs issue may arise
        if 'create_uid' in fields_list and 'create_uid' not in result:
            result['create_uid'] = self.env.uid

        return {
            fname: result[fname]
            for fname in result if fname in fields_list
        }

    # content
    subject = fields.Char(
        'Subject',
        compute='_compute_subject', readonly=False, store=True)
    body = fields.Html(
        'Contents',
        render_engine='qweb', render_options={'post_process': True},
        sanitize_style=True,
        compute='_compute_body', readonly=False, store=True)
    parent_id = fields.Many2one(
        'mail.message', 'Parent Message', ondelete='set null')
    template_id = fields.Many2one(
        'mail.template', 'Use template',
        domain="[('model', '=', model), '|', ('user_id','=', False), ('user_id', '=', uid)]"
    )
    attachment_ids = fields.Many2many(
        'ir.attachment', 'mail_compose_message_ir_attachments_rel',
        'wizard_id', 'attachment_id', string='Attachments',
        compute='_compute_attachment_ids', readonly=False, store=True)
    email_layout_xmlid = fields.Char(
        'Email Notification Layout',
        compute='_compute_email_layout_xmlid', readonly=False, store=True,
        copy=False, compute_sudo=False)
    email_add_signature = fields.Boolean(
        'Add signature',
        compute='_compute_email_add_signature', readonly=False, store=True)
    # origin
    email_from = fields.Char(
        'From', compute='_compute_authorship', readonly=False, store=True, compute_sudo=False,
        help="Email address of the sender. This field is set when no matching partner is found and replaces the author_id field in the chatter.")
    author_id = fields.Many2one(
        'res.partner', string='Author',
        compute='_compute_authorship', readonly=False, store=True, compute_sudo=False,
        help="Author of the message. If not set, email_from may hold an email address that did not match any partner.")
    # composition
    composition_mode = fields.Selection(
        selection=[('comment', 'Post on a document'),
                   ('mass_mail', 'Email Mass Mailing')],
        string='Composition mode', default='comment')
    composition_batch = fields.Boolean(
        'Batch composition', compute='_compute_composition_batch')  # more than 1 record (raw source)
    model = fields.Char('Related Document Model', compute='_compute_model', readonly=False, store=True)
    model_is_thread = fields.Boolean('Thread-Enabled', compute='_compute_model_is_thread')
    res_ids = fields.Text('Related Document IDs', compute='_compute_res_ids', readonly=False, store=True)
    res_domain = fields.Text('Active domain')
    res_domain_user_id = fields.Many2one(
        'res.users', string='Responsible',
        help='Used as context used to evaluate composer domain')
    record_alias_domain_id = fields.Many2one(
        'mail.alias.domain', 'Alias Domain',
        compute='_compute_record_environment', readonly=False, store=True)  # useful only in monorecord comment mode
    record_company_id = fields.Many2one(
        'res.company', 'Company',
        compute='_compute_record_environment', readonly=False, store=True)  # useful only in monorecord comment mode
    record_name = fields.Char(
        'Record Name',
        compute='_compute_record_name', readonly=False, store=True)  # useful only in monorecord comment mode
    # characteristics
    message_type = fields.Selection([
        ('auto_comment', 'Automated Targeted Notification'),
        ('comment', 'Comment'),
        ('notification', 'System notification')],
        'Type', required=True, default='comment',
        help="Message type: email for email message, notification for system "
             "message, comment for other messages such as user replies")
    subtype_id = fields.Many2one(
        'mail.message.subtype', 'Subtype', ondelete='set null',
        compute="_compute_subtype_id", readonly=False, store=True)
    subtype_is_log = fields.Boolean('Is a log', compute='_compute_subtype_is_log')
    mail_activity_type_id = fields.Many2one('mail.activity.type', 'Mail Activity Type', ondelete='set null')
    # destination
    reply_to = fields.Char(
        'Reply To', compute='_compute_reply_to', readonly=False, store=True, compute_sudo=False,
        help='Reply email address. Setting the reply_to bypasses the automatic thread creation.')
    reply_to_force_new = fields.Boolean(
        string='Considers answers as new thread',
        compute='_compute_reply_to_force_new', readonly=False, store=True,
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
        compute='_compute_partner_ids', readonly=False, store=True)
    # sending
    auto_delete = fields.Boolean(
        'Delete Emails',
        compute="_compute_auto_delete", readonly=False, store=True, compute_sudo=False,
        help='This option permanently removes any track of email after it\'s been sent, including from the Technical menu in the Settings, in order to preserve storage space of your Odoo database.')
    auto_delete_keep_log = fields.Boolean(
        'Keep Message Copy',
        compute="_compute_auto_delete_keep_log", readonly=False, store=True,
        help='Keep a copy of the email content if emails are removed (mass mailing only)')
    force_send = fields.Boolean(
        'Send mailing or notifications directly',
        compute='_compute_force_send', readonly=False, store=True)
    mail_server_id = fields.Many2one(
        'ir.mail_server', string='Outgoing mail server',
        compute='_compute_mail_server_id', readonly=False, store=True, compute_sudo=False)
    scheduled_date = fields.Char(
        'Scheduled Date',
        compute='_compute_scheduled_date', readonly=False, store=True, compute_sudo=False,
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

    @api.depends('composition_mode', 'model', 'parent_id', 'record_name',
                 'res_domain', 'res_ids', 'template_id')
    def _compute_subject(self):
        """ Computation is coming either form template, either from context.
        When having a template with a value set, copy it (in batch mode) or
        render it (in monorecord comment mode) on the composer. Otherwise
        it comes from the parent (if set), or computed based on the generic
        '_message_compute_subject' method in monorecord comment mode, or
        set to False. When removing the template, reset it. """
        for composer in self:
            if composer.template_id:
                composer._set_value_from_template('subject')
            if not composer.template_id or not composer.subject:
                subject = composer.parent_id.subject
                if (not subject and composer.model and
                    composer.composition_mode == 'comment' and
                    not composer.composition_batch):
                    if composer.model_is_thread:
                        res_ids = composer._evaluate_res_ids()
                        subject = self.env[composer.model].browse(res_ids)._message_compute_subject()
                    else:
                        subject = composer.record_name
                composer.subject = subject

    @api.depends('composition_mode', 'model', 'res_domain', 'res_ids',
                 'template_id')
    def _compute_body(self):
        """ Computation is coming either from template, either reset. When
        having a template with a value set, copy it (in batch mode) or render
        it (in monorecord comment mode) on the composer. When removing the
        template, reset it. """
        for composer in self:
            if composer.template_id:
                composer._set_value_from_template('body_html', 'body')
            if not composer.template_id:
                composer.body = False

    @api.depends('composition_mode', 'model', 'res_domain', 'res_ids', 'template_id')
    def _compute_attachment_ids(self):
        """ Computation is based on template and composition mode. In monorecord
        comment mode, template is used to generate attachments based on both
        attachment_ids of template, and reports coming from report_template_ids.
        Those are generated based on the current record to display. As template
        generation returns a list of tuples, new attachments are created on
        the fly during the compute.

        In batch or email mode, only attachment_ids from template are used on
        the composer. Reports will be generated at sending time.

        When template is removed, attachments are reset. """
        for composer in self:
            res_ids = composer._evaluate_res_ids() or [0]
            if (composer.template_id.attachment_ids and
                (composer.composition_mode == 'mass_mail' or composer.composition_batch)):
                composer.attachment_ids = composer.template_id.attachment_ids
            elif composer.template_id and composer.composition_mode == 'comment' and len(res_ids) == 1:
                rendered_values = composer._generate_template_for_composer(
                    res_ids,
                    ('attachment_ids', 'attachments'),
                )[res_ids[0]]
                attachment_ids = rendered_values.get('attachment_ids') or []
                # transform attachments into attachment_ids; not attached to the
                # document because this will be done further in the posting
                # process, allowing to clean database if email not send
                if rendered_values.get('attachments'):
                    attachment_ids += self.env['ir.attachment'].create([
                        {'name': attach_fname,
                         'datas': attach_datas,
                         'res_model': 'mail.compose.message',
                         'res_id': 0,
                         'type': 'binary',    # override default_type from context, possibly meant for another model!
                        } for attach_fname, attach_datas in rendered_values.pop('attachments')
                    ]).ids
                if attachment_ids:
                    composer.attachment_ids = attachment_ids
            elif not composer.template_id:
                composer.attachment_ids = False

    @api.depends('template_id')
    def _compute_email_add_signature(self):
        """ When having a template, consider it defines completely body and
        do not add signature. Without template, add signature by default
        in comment due to post processing for notification emails. Mailing
        mode does not handle signature. """
        for composer in self:
            if composer.composition_mode == 'mass_mail':
                composer.email_add_signature = False  # not supported
            else:
                composer.email_add_signature = not bool(composer.template_id)

    @api.depends('template_id')
    def _compute_email_layout_xmlid(self):
        """ Computation is coming either from template, either reset. When
        having a template with a value set, set it on composer.When removing
        the template, reset it. """
        for composer in self:
            if composer.template_id.email_layout_xmlid:
                composer.email_layout_xmlid = composer.template_id.email_layout_xmlid
            if not composer.template_id:
                composer.email_layout_xmlid = False

    @api.depends('composition_mode', 'email_from', 'model',
                 'res_domain', 'res_ids', 'template_id')
    def _compute_authorship(self):
        """ Computation is coming either from template, either from context.
        When having a template with a value set, copy it (in batch mode) or
        render it (in monorecord comment mode) on the composer. Otherwise
        try to take current user's email. When removing the template, fallback
        on default thread behavior (which is current user's email).

        Author is not controllable from the template currently. We therefore
        try to synchronize it with the given email_from (in rendered mode to
        avoid trying to find partner based on qweb expressions), or fallback
        on current user. """
        Thread = self.env['mail.thread'].with_context(active_test=False)
        for composer in self:
            rendering_mode = composer.composition_mode == 'comment' and not composer.composition_batch
            updated_author_id = None

            # update email_from first as it is the main used field currently
            if composer.template_id.email_from:
                composer._set_value_from_template('email_from')
            # switch to a template without email_from -> fallback on current user as default
            elif composer.template_id:
                composer.email_from = self.env.user.email_formatted
            # removing template or void from -> fallback on current user as default
            elif not composer.template_id or not composer.email_from:
                composer.email_from = self.env.user.email_formatted
                updated_author_id = self.env.user.partner_id.id

            # Update author. When being in rendered mode: link with rendered
            # email_from or fallback on current user if email does not match.
            # When changing template in raw mode or resetting also fallback.
            if composer.email_from and rendering_mode and not updated_author_id:
                updated_author_id, _ = Thread._message_compute_author(
                    None, composer.email_from, raise_on_email=False,
                )
                if not updated_author_id:
                    updated_author_id = self.env.user.partner_id.id
            if not rendering_mode or not composer.template_id:
                updated_author_id = self.env.user.partner_id.id

            if updated_author_id:
                composer.author_id = updated_author_id

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

    @api.depends('composition_mode', 'parent_id')
    def _compute_model(self):
        """ Model can be set from parent or using 'active_model' context key
        frequently used as the composer is most invoked from list or form
        views. """
        for composer in self:
            if composer.parent_id and composer.composition_mode == 'comment':
                composer.model = composer.parent_id.model
            elif not composer.model:
                composer.model = self.env.context.get('active_model')

    @api.depends('model')
    def _compute_model_is_thread(self):
        """ Determine if model is thread enabled. """
        for composer in self:
            model = self.env['ir.model']._get(composer.model)
            composer.model_is_thread = model.is_mail_thread

    @api.depends('composition_mode', 'parent_id')
    def _compute_res_ids(self):
        """ Computation may come from parent in comment mode, if set. It takes
        the parent message's res_id. Otherwise the composer uses the 'active_ids'
        context key, unless it is too big to be stored in database. Indeed
        when invoked for big mailings, 'active_ids' may be a very big list.
        Support of 'active_ids' when sending is granted in order to not always
        rely on 'res_ids' field. When 'active_ids' is not present, fallback
        on 'active_id'. """
        for composer in self.filtered(lambda composer: not composer.res_ids):
            if composer.parent_id and composer.composition_mode == 'comment':
                composer.res_ids = f"{[composer.parent_id.res_id]}"
            else:
                active_res_ids = parse_res_ids(self.env.context.get('active_ids'))
                # beware, field is limited in storage, usage of active_ids in context still required
                if active_res_ids and len(active_res_ids) <= 500:
                    composer.res_ids = f"{self.env.context['active_ids']}"
                elif not active_res_ids and self.env.context.get('active_id'):
                    composer.res_ids = f"{[self.env.context['active_id']]}"

    @api.depends('composition_mode', 'model', 'res_domain', 'res_ids')
    def _compute_record_environment(self):
        """ In monorecord mode, fetch record company and the linked alias domain,
        easing future processing notably at post and notification sending time.

        In batch mode it makes no sense to compute a single company, it will be
        dynamically generated. """
        toreset = self.filtered(
            lambda comp: (comp.record_company_id or comp.record_alias_domain_id) and comp.composition_batch
        )
        if toreset:
            toreset.record_alias_domain_id = False
            toreset.record_company_id = False

        toupdate = self.filtered(
            lambda comp: not comp.composition_batch
        )
        for composer in toupdate:
            res_ids = composer._evaluate_res_ids()
            if composer.model in self.env and len(res_ids) == 1:
                record = self.env[composer.model].browse(res_ids)
                composer.record_company_id = record._mail_get_companies(
                    default=self.env.company
                )[record.id]
                composer.record_alias_domain_id = record._mail_get_alias_domains(
                    default_company=self.env.company
                )[record.id]

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

    @api.depends('composition_mode')
    def _compute_subtype_id(self):
        """ Computation defaults from composition mode. Subtype is not used in
        mass mail mode, and is comment for comment mode. """
        comment_composers = self.filtered(lambda comp: comp.composition_mode == 'comment')
        if comment_composers:
            comment_composers.subtype_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment')
        (self - comment_composers).subtype_id = False

    @api.depends('subtype_id')
    def _compute_subtype_is_log(self):
        """ In comment mode, tells whether the subtype is a note. Subtype has
        no use in email mode, and this field will be False. """
        note_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note')
        self.subtype_is_log = False
        for composer in self.filtered('subtype_id'):
            composer.subtype_is_log = composer.subtype_id.id == note_id

    @api.depends('composition_mode', 'model', 'res_domain', 'res_ids',
                 'template_id')
    def _compute_reply_to(self):
        """ Computation is coming either from template, either reset. When
        having a template with a value set, copy it (in batch mode) or render
        it (in monorecord comment mode) on the composer. When removing the
        template, reset it. """
        for composer in self:
            if composer.template_id:
                composer._set_value_from_template('reply_to')
            else:
                composer.reply_to = False

    @api.depends('model')
    def _compute_reply_to_force_new(self):
        """ If model does not inherit from MailThread, avoid replies to be
        considered as thread updates, they will instead follow the routing
        rules (alias, ...). """
        self.filtered(
            lambda composer: not composer.model or not composer.model_is_thread
        ).reply_to_force_new = True

    @api.depends('reply_to_force_new')
    def _compute_reply_to_mode(self):
        for composer in self:
            composer.reply_to_mode = 'new' if composer.reply_to_force_new else 'update'

    def _inverse_reply_to_mode(self):
        for composer in self:
            composer.reply_to_force_new = composer.reply_to_mode == 'new'

    @api.depends('composition_mode', 'model', 'parent_id', 'res_domain',
                 'res_ids', 'template_id')
    def _compute_partner_ids(self):
        """ Computation is coming either from template, either from context.
        When having a template it uses its 3 fields 'email_cc', 'email_to' and
        'partner_to', in monorecord comment mode. Emails are converted into
        partners, creating new ones when the email does not match any existing
        partner. Composer does not deal with emails but only with partners.
        When having a template in other modes, no recipients are computed
        as it is done at sending time. When removing the template, reset it.

        When not having a template, recipients may come from the parent in
        comment mode, to be sure to notify the same people. """
        for composer in self:
            if (composer.template_id and composer.composition_mode == 'comment'
                and not composer.composition_batch):
                res_ids = composer._evaluate_res_ids() or [0]
                rendered_values = composer._generate_template_for_composer(
                    res_ids,
                    {'email_cc', 'email_to', 'partner_ids'},
                    find_or_create_partners=True,
                )[res_ids[0]]
                if rendered_values.get('partner_ids'):
                    composer.partner_ids = rendered_values['partner_ids']
            elif composer.parent_id and composer.composition_mode == 'comment':
                composer.partner_ids = composer.parent_id.partner_ids
            elif not composer.template_id:
                composer.partner_ids = False

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

    @api.depends('composition_mode', 'model', 'res_domain', 'res_ids')
    def _compute_force_send(self):
        """ When being in single record mode, we force_send (post on a record
        or send a single email right away). In batch mode: comment always uses
        the email queue (lot of potentially different emails to craft). Mass
        mailing mode depends on number of recipients and is configurable using
        'mail.mail.force.send.limit' configuration parameter (default=100).
        Using a domain forces the email queue usage as it depends on actual
        evaluation and is generally used for big batches anyway. """
        for composer in self:
            if not composer.composition_batch:
                composer.force_send = True
            elif composer.composition_mode == 'comment' or composer.res_domain:
                composer.force_send = False
            else:
                force_send_limit = int(self.env['ir.config_parameter'].sudo().get_param('mail.mail.force.send.limit', 100))
                res_ids = composer._evaluate_res_ids()
                composer.force_send = len(res_ids) <= force_send_limit

    @api.depends('template_id')
    def _compute_mail_server_id(self):
        """ Copy value from template when updating it, if set on template. When
        removing the template, reset it. """
        for composer in self:
            if composer.template_id.mail_server_id:
                composer.mail_server_id = composer.template_id.mail_server_id
            if not composer.template_id:
                composer.mail_server_id = False

    @api.depends('composition_mode', 'model', 'res_ids', 'template_id')
    def _compute_scheduled_date(self):
        """ Computation is coming either from template, either reset. When
        having a template with a value set, copy it (in batch mode) or render
        it (in monorecord comment mode) on the composer. When removing the
        template, reset it. """
        for composer in self:
            if composer.template_id:
                composer._set_value_from_template('scheduled_date')
            if not composer.template_id:
                composer.scheduled_date = False

    # Overrides of mail.compose.mixin
    @api.depends('template_id')
    def _compute_lang(self):
        """ Computation is coming either from template, either reset. When
        having a template with a value set, copy it (in batch mode) or render
        it (in monorecord comment mode) on the composer. When removing the
        template, reset it. """
        for composer in self:
            if composer.template_id:
                composer._set_value_from_template('lang')
            if not composer.template_id:
                composer.lang = False

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

    def _compute_field_value(self, field):
        if field.compute_sudo:
            return super(MailComposer, self.with_context(prefetch_fields=False))._compute_field_value(field)
        return super()._compute_field_value(field)

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
                res_ids = self.env[wizard.model].search(search_domain).ids
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

        batch_size = int(
            self.env['ir.config_parameter'].sudo().get_param('mail.batch_size')
        ) or self._batch_size or 50  # be sure to not have 0, as otherwise no iteration is done
        for res_ids_iter in tools.split_every(batch_size, res_ids):
            res_ids_values = list(self._prepare_mail_values(res_ids_iter).values())

            iter_mails_sudo = self.env['mail.mail'].sudo().create(res_ids_values)
            mails_sudo += iter_mails_sudo

            records = self.env[self.model].browse(res_ids_iter) if self.model and hasattr(self.env[self.model], 'message_post') else False
            if records:
                records._message_mail_after_hook(iter_mails_sudo)

            if self.force_send:
                # as 'send' does not filter out scheduled mails (only 'process_email_queue'
                # does) we need to do it manually
                iter_mails_sudo_tosend = iter_mails_sudo.filtered(
                    lambda mail: (
                        not mail.scheduled_date or
                        mail.scheduled_date <= datetime.datetime.utcnow()
                    )
                )
                if iter_mails_sudo_tosend:
                    iter_mails_sudo_tosend.send(auto_commit=auto_commit)
                    continue
            # sending emails will commit and invalidate cache; in case we do not force
            # send better void the cache and commit what is already generated to avoid
            # running several times on same records in case of issue
            if auto_commit is True:
                self._cr.commit()
            self.env.invalidate_all()

        return mails_sudo

    def open_template_creation_wizard(self):
        """ hit save as template button: opens a wizard that prompts for the template's subject.
            `create_mail_template` is called when saving the new wizard. """

        self.ensure_one()
        saved_subject = self.subject
        self.subject = False
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_id': self.env.ref('mail.mail_compose_message_view_form_template_save').id,
            'name': _('Create a new Mail Template'),
            'res_model': 'mail.compose.message',
            'context': {'dialog_size': 'medium', 'mail_composer_saved_subject': saved_subject},
            'target': 'new',
            'res_id': self.id,
        }

    def create_mail_template(self):
        """ creates a mail template with the current mail composer's fields """
        self.ensure_one()
        if not self.model or not self.model in self.env:
            raise UserError(_('Template creation from composer requires a valid model.'))
        model_id = self.env['ir.model']._get_id(self.model)
        values = {
            'name': self.subject,
            'subject': self.subject,
            'body_html': self.body,
            'model_id': model_id,
            'use_default_to': True,
            'user_id': self.env.uid,
        }
        template = self.env['mail.template'].create(values)

        if self.attachment_ids:
            attachments = self.env['ir.attachment'].sudo().browse(self.attachment_ids.ids).filtered(
                lambda a: a.res_model == 'mail.compose.message' and a.create_uid.id == self._uid)
            if attachments:
                attachments.write({'res_model': template._name, 'res_id': template.id})
                template.attachment_ids = self.attachment_ids

        # generate the saved template
        self.write({'template_id': template.id})
        return _reopen(self, self.id, self.model, context={**self.env.context, 'dialog_size': 'large'})

    def cancel_save_template(self):
        """ Restore old subject when canceling the 'save as template' action
            as it was erased to let user give a more custom input. """
        self.ensure_one()
        self.subject = self.env.context.get('mail_composer_saved_subject')
        return _reopen(self, self.id, self.model, context={**self.env.context, 'dialog_size': 'large'})

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
            DYN - 'force_email_lang',  # notify parameter
            STA - 'record_alias_domain_id',  # monorecord only
            STA - 'record_company_id',  # monorecord only

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
            'message_type': 'email_outgoing' if email_mode else self.message_type,
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
                email_add_signature=self.email_add_signature,
                email_layout_xmlid=self.email_layout_xmlid,
                force_send=self.force_send,
                mail_auto_delete=self.auto_delete,
                model_description=model_description,
                record_alias_domain_id=self.record_alias_domain_id.id,
                record_company_id=self.record_company_id.id,
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

        # records values
        companies = RecordsModel.browse(res_ids)._mail_get_companies(default=self.env.company)
        alias_domains = RecordsModel.browse(res_ids)._mail_get_alias_domains(default_company=self.env.company)

        # langs, used currently only to propagate in comment mode for notification
        # layout translation
        langs = self._render_field('lang', res_ids)
        subjects = self._render_field('subject', res_ids, compute_lang=True)
        bodies = self._render_field(
            'body', res_ids, compute_lang=True,
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
                # record-specific environment values (company, alias_domain)
                'record_alias_domain_id': alias_domains[res_id].id,
                'record_company_id': companies[res_id].id,
                # some fields are specific to mail
                **(
                    {
                        'body_html': bodies[res_id],
                        'res_id': res_id,
                    } if email_mode else {}
                ),
                # some fields are specific to message
                **(
                    {
                        # notify parameter to force layout lang
                        'force_email_lang': langs[res_id],
                    } if not email_mode else {}
                ),
            }
            for res_id in res_ids
        }

        # generate template-based values
        if self.template_id:
            template_values = self._generate_template_for_composer(
                res_ids,
                ('attachment_ids',
                 'email_to',
                 'email_cc',
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
        if not self.template_id and not self.partner_ids and email_mode:
            default_recipients = RecordsModel.browse(res_ids)._message_get_default_recipients()
            for res_id in res_ids:
                mail_values_all[res_id].update(
                    default_recipients.get(res_id, {})
                )
        # TDE FIXME: seems to be missing an "else" here to add partner_ids in rendering mode

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
                process_record = record if hasattr(record, "_process_attachments_for_post") else record.env["mail.thread"]
                mail_values['attachment_ids'] = process_record._process_attachments_for_post(
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
                recipient_ids_all = set(mail_values.pop('partner_ids', [])) | set(self.partner_ids.ids)
                mail_values['recipient_ids'] = [(4, pid) for pid in recipient_ids_all]

            # when having no specific reply_to -> fetch rendered email_from
            if email_mode:
                reply_to = reply_to_values.get(res_id)
                if not reply_to:
                    reply_to = mail_values.get('email_from', False)
                mail_values['reply_to'] = reply_to

            # body: render layout in email mode (comment mode is managed by the
            # notification process, see @_notify_thread_by_email)
            if email_mode and self.email_layout_xmlid and mail_values['recipient_ids']:
                lang = langs[res_id]
                recipient_ids = [command[1] for command in mail_values['recipient_ids']]
                msg_vals = {
                    'email_layout_xmlid': self.email_layout_xmlid,
                    'model': self.model,
                    'res_id': res_id,
                }
                message_inmem = self.env['mail.message'].new({
                    'body': mail_values['body'],
                })
                for _lang, render_values, recipients_group_data in record._notify_get_classified_recipients_iterator(
                    message_inmem,
                    [{
                        'active': True,
                        'id': pid,
                        'lang': lang,
                        'notif': 'email',
                        'share': True,
                        'type': 'customer',
                        'ushare': False,
                    } for pid in recipient_ids],
                    msg_vals=msg_vals,
                    model_description=False,  # force dynamic computation
                    force_email_lang=lang,
                ):
                    mail_body = record._notify_by_email_render_layout(
                        message_inmem,
                        recipients_group_data,
                        msg_vals=msg_vals,
                        render_values=render_values,
                    )
                    mail_values['body_html'] = mail_body

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
        email_mode = self.composition_mode == 'mass_mail'

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
                **(
                    {
                        # notify parameter to force layout lang
                        'force_email_lang': self.lang,
                    } if not email_mode else {}
                ),
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
        blacklist_ids = self._get_blacklist_record_ids(mail_values_dict, recipients_info)
        optout_emails = self._get_optout_emails(mail_values_dict)
        done_emails = self._get_done_emails(mail_values_dict)
        sent_emails_mapping = {}  # distinct emails sent to each address as {email_address: [mail_values]}

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
            elif mail_to in done_emails:
                mail_values['state'] = 'cancel'
                mail_values['failure_type'] = 'mail_dup'
            # void of falsy values -> error
            elif not mail_to:
                mail_values['state'] = 'cancel'
                mail_values['failure_type'] = 'mail_email_missing'
            elif not mail_to_normalized:
                mail_values['state'] = 'cancel'
                mail_values['failure_type'] = 'mail_email_invalid'
            elif mail_to in sent_emails_mapping:
                # If the number of attachments on the mail exactly matches the number of attachments on the composer
                # we assume the attachments are copies of the ones attached to the composer and thus are the same
                if len(self.attachment_ids) == len(mail_values.get('attachment_ids', [])) and\
                   any(sent_mail.get('subject') == mail_values.get('subject') and
                       sent_mail.get('body') == mail_values.get('body') for sent_mail in sent_emails_mapping[mail_to]):
                    mail_values['state'] = 'cancel'
                    mail_values['failure_type'] = 'mail_dup'
                else:
                    sent_emails_mapping[mail_to].append(mail_values)
            else:
                sent_emails_mapping[mail_to] = [mail_values]

        done_emails += sent_emails_mapping.keys()

        return mail_values_dict

    def _generate_template_for_composer(self, res_ids, render_fields,
                                        find_or_create_partners=True):
        """ Generate values based on template and relevant values for the
        mail.compose.message wizard.

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
        template_values = self.template_id._generate_template(
            res_ids,
            template_fields,
            find_or_create_partners=find_or_create_partners,
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

    def _get_blacklist_record_ids(self, mail_values_dict, recipients_info=None):
        blacklisted_rec_ids = set()
        if not self.use_exclusion_list:
            return blacklisted_rec_ids
        if self.composition_mode == 'mass_mail':
            self.env['mail.blacklist'].flush_model(['email', 'active'])
            self._cr.execute("SELECT email FROM mail_blacklist WHERE active=true")
            blacklist = {x[0] for x in self._cr.fetchall()}
            if not blacklist:
                return blacklisted_rec_ids
            if isinstance(self.env[self.model], self.pool['mail.thread.blacklist']):
                targets = self.env[self.model].browse(mail_values_dict.keys())
                targets.fetch(['email_normalized'])
                # First extract email from recipient before comparing with blacklist
                blacklisted_rec_ids.update(target.id for target in targets
                                           if target.email_normalized in blacklist)
            elif recipients_info:
                # Note that we exclude the record if at least one recipient is blacklisted (-> even if not all)
                # But as commented above: Mass mailing should always have a single recipient per record.
                blacklisted_rec_ids.update(res_id for res_id, recipient_info in recipients_info.items()
                                           if blacklist & set(recipient_info['mail_to_normalized']))
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
            # add email from email_to; if unrecognized email in email_to keep
            # it as used for further processing
            mail_to = tools.email_split_and_format(mail_values.get('email_to'))
            if not mail_to and mail_values.get('email_to'):
                mail_to.append(mail_values['email_to'])
            # add email from recipients (res.partner)
            mail_to += [
                recipient_emails[recipient_command[1]]
                for recipient_command in mail_values.get('recipient_ids') or []
                if recipient_command[1]
            ]
            # uniquify, keep ordering
            seen = set()
            mail_to = [email for email in mail_to if email not in seen and not seen.add(email)]
            recipients_info[record_id] = {
                'mail_to': mail_to,
                'mail_to_normalized': [
                    tools.email_normalize(mail, strict=False)
                    for mail in mail_to
                    if tools.email_normalize(mail, strict=False)
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
        return parse_res_ids(
            self.env.context.get('composer_force_res_ids') or
            self.res_ids or
            self.env.context.get('active_ids')
        ) or []

    def _set_value_from_template(self, template_fname, composer_fname=False):
        """ Set composer value from its template counterpart. In monorecord
        comment mode, we get directly the rendered value, giving the real
        value to the user. Otherwise we get the raw (unrendered) value from
        template, as it will be rendered at send time (for mass mail, whatever
        the number of contextual records to mail) or before posting on records
        (for comment in batch).

        :param str template_fname: name of field on template model, used to
          fetch the value (and maybe render it);
        :param str composer_fname: name of field on composer model, when field
          names do not match (e.g. body_html on template used to populate body
          on composer);
        """
        self.ensure_one()
        composer_fname = composer_fname or template_fname

        # fetch template value, check if void
        template_value = self.template_id[template_fname] if self.template_id else False
        if template_value and template_fname == 'body_html':
            template_value = template_value if not is_html_empty(template_value) else False

        if template_value:
            if self.composition_mode == 'comment' and not self.composition_batch:
                res_ids = self._evaluate_res_ids()
                rendering_res_ids = res_ids or [0]
                self[composer_fname] = self.template_id._generate_template(
                    rendering_res_ids,
                    {template_fname},
                )[rendering_res_ids[0]][template_fname]
            else:
                self[composer_fname] = self.template_id[template_fname]
        return self[composer_fname]
