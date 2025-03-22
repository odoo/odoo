# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import base64
import re

from odoo import _, api, fields, models, tools, Command
from odoo.exceptions import UserError
from odoo.osv import expression


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
    def default_get(self, fields):
        """ Handle composition mode. Some details about context keys:
            - comment: default mode, model and ID of a record the user comments
                - default_model or active_model
                - default_res_id or active_id
            - mass_mail: model and IDs of records the user mass-mails
                - active_ids: record IDs
                - default_model or active_model
        """
        # backward compatibility of context before addition of
        # email_layout_xmlid field: to remove in 15.1+
        if self._context.get('custom_layout') and 'default_email_layout_xmlid' not in self._context:
            self = self.with_context(default_email_layout_xmlid=self._context['custom_layout'])

        result = super(MailComposer, self).default_get(fields)

        # author
        missing_author = 'author_id' in fields and 'author_id' not in result
        missing_email_from = 'email_from' in fields and 'email_from' not in result
        if missing_author or missing_email_from:
            author_id, email_from = self.env['mail.thread']._message_compute_author(result.get('author_id'), result.get('email_from'), raise_on_email=False)
            if missing_email_from:
                result['email_from'] = email_from
            if missing_author:
                result['author_id'] = author_id

        if 'model' in fields and 'model' not in result:
            result['model'] = self._context.get('active_model')
        if 'res_id' in fields and 'res_id' not in result:
            result['res_id'] = self._context.get('active_id')
        if 'reply_to_mode' in fields and 'reply_to_mode' not in result and result.get('model'):
            # doesn't support threading
            if result['model'] not in self.env or not hasattr(self.env[result['model']], 'message_post'):
                result['reply_to_mode'] = 'new'

        if 'active_domain' in self._context:  # not context.get() because we want to keep global [] domains
            result['active_domain'] = '%s' % self._context.get('active_domain')
        if result.get('composition_mode') == 'comment' and (set(fields) & set(['model', 'res_id', 'partner_ids', 'record_name', 'subject'])):
            result.update(self.get_record_data(result))

        # when being in new mode, create_uid is not granted -> ACLs issue may arise
        if 'create_uid' in fields and 'create_uid' not in result:
            result['create_uid'] = self.env.uid

        filtered_result = dict((fname, result[fname]) for fname in result if fname in fields)
        return filtered_result

    def _partner_ids_domain(self):
        return expression.OR([
            [('type', '!=', 'private')],
            [('id', 'in', self.env.context.get('default_partner_ids', []))],
        ])

    # content
    subject = fields.Char('Subject', compute=False)
    body = fields.Html('Contents', render_engine='qweb', compute=False, default='', sanitize_style=True)
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
    composition_mode = fields.Selection(selection=[
        ('comment', 'Post on a document'),
        ('mass_mail', 'Email Mass Mailing'),
        ('mass_post', 'Post on Multiple Documents')], string='Composition mode', default='comment')
    model = fields.Char('Related Document Model')
    res_id = fields.Integer('Related Document ID')
    record_name = fields.Char('Message Record Name')
    use_active_domain = fields.Boolean('Use active domain')
    active_domain = fields.Text('Active domain', readonly=True)
    # characteristics
    message_type = fields.Selection([
        ('auto_comment', 'Automated Targeted Notification'),
        ('comment', 'Comment'),
        ('notification', 'System notification')],
        'Type', required=True, default='comment',
        help="Message type: email for email message, notification for system "
             "message, comment for other messages such as user replies")
    is_log = fields.Boolean('Log as Internal Note')
    subtype_id = fields.Many2one(
        'mail.message.subtype', 'Subtype', ondelete='set null',
        default=lambda self: self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment'))
    notify = fields.Boolean('Notify followers', help='Notify followers of the document (mass post only)')
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
    auto_delete = fields.Boolean('Delete Emails',
        help='This option permanently removes any track of email after it\'s been sent, including from the Technical menu in the Settings, in order to preserve storage space of your Odoo database.')
    auto_delete_message = fields.Boolean('Delete Message Copy', help='Do not keep a copy of the email in the document communication history (mass mailing only)')
    mail_server_id = fields.Many2one('ir.mail_server', 'Outgoing mail server')

    @api.depends('reply_to_force_new')
    def _compute_reply_to_mode(self):
        for composer in self:
            composer.reply_to_mode = 'new' if composer.reply_to_force_new else 'update'

    def _inverse_reply_to_mode(self):
        for composer in self:
            composer.reply_to_force_new = composer.reply_to_mode == 'new'

    # Overrides of mail.render.mixin
    @api.depends('model')
    def _compute_render_model(self):
        for composer in self:
            composer.render_model = composer.model

    # Onchanges

    @api.onchange('template_id')
    def _onchange_template_id_wrapper(self):
        self.ensure_one()
        values = self._onchange_template_id(self.template_id.id, self.composition_mode, self.model, self.res_id)['value']
        for fname, value in values.items():
            setattr(self, fname, value)

    def _compute_can_edit_body(self):
        """Can edit the body if we are not in "mass_mail" mode because the template is
        rendered before it's modified.
        """
        non_mass_mail = self.filtered(lambda m: m.composition_mode != 'mass_mail')
        non_mass_mail.can_edit_body = True
        super(MailComposer, self - non_mass_mail)._compute_can_edit_body()

    @api.model
    def get_record_data(self, values):
        """ Returns a defaults-like dict with initial values for the composition
        wizard when sending an email related a previous email (parent_id) or
        a document (model, res_id). This is based on previously computed default
        values. """
        result, subject = {}, False
        if values.get('parent_id'):
            parent = self.env['mail.message'].browse(values.get('parent_id'))
            result['record_name'] = parent.record_name
            subject = tools.ustr(parent.subject or parent.record_name or '')
            if not values.get('model'):
                result['model'] = parent.model
            if not values.get('res_id'):
                result['res_id'] = parent.res_id
            partner_ids = values.get('partner_ids', list()) + parent.partner_ids.ids
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
        # Several custom layouts make use of the model description at rendering, e.g. in the
        # 'View <document>' button. Some models are used for different business concepts, such as
        # 'purchase.order' which is used for a RFQ and and PO. To avoid confusion, we must use a
        # different wording depending on the state of the object.
        # Therefore, we can set the description in the context from the beginning to avoid falling
        # back on the regular display_name retrieved in ``_notify_by_email_prepare_rendering_context()``.
        model_description = self._context.get('model_description')
        result_mails_su, result_messages = self.env['mail.mail'].sudo(), self.env['mail.message']

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
                new_attachment_ids.reverse()
                wizard.write({'attachment_ids': [Command.set(new_attachment_ids)]})

            # Mass Mailing
            mass_mode = wizard.composition_mode in ('mass_mail', 'mass_post')

            ActiveModel = self.env[wizard.model] if wizard.model and hasattr(self.env[wizard.model], 'message_post') else self.env['mail.thread']
            if wizard.composition_mode == 'mass_post':
                # do not send emails directly but use the queue instead
                # add context key to avoid subscribing the author
                ActiveModel = ActiveModel.with_context(mail_notify_force_send=False, mail_create_nosubscribe=True)
            # wizard works in batch mode: [res_id] or active_ids or active_domain
            if mass_mode and wizard.use_active_domain and wizard.model:
                res_ids = self.env[wizard.model].search(ast.literal_eval(wizard.active_domain)).ids
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
                subtype_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment')

            for res_ids in sliced_res_ids:
                # mass mail mode: mail are sudo-ed, as when going through get_mail_values
                # standard access rights on related records will be checked when browsing them
                # to compute mail values. If people have access to the records they have rights
                # to create lots of emails in sudo as it is consdiered as a technical model.
                batch_mails_sudo = self.env['mail.mail'].sudo()
                all_mail_values = wizard.get_mail_values(res_ids)
                for res_id, mail_values in all_mail_values.items():
                    if wizard.composition_mode == 'mass_mail':
                        batch_mails_sudo += self.env['mail.mail'].sudo().create(mail_values)
                    else:
                        post_params = dict(
                            subtype_id=subtype_id,
                            email_layout_xmlid=wizard.email_layout_xmlid,
                            email_add_signature=not bool(wizard.template_id) and wizard.email_add_signature,
                            mail_auto_delete=wizard.template_id.auto_delete if wizard.template_id else self._context.get('mail_auto_delete', True),
                            model_description=model_description)
                        post_params.update(mail_values)
                        if ActiveModel._name == 'mail.thread':
                            if wizard.model:
                                post_params['model'] = wizard.model
                                post_params['res_id'] = res_id
                            if not ActiveModel.message_notify(**post_params):
                                # if message_notify returns an empty record set, no recipients where found.
                                raise UserError(_("No recipient found."))
                        else:
                            result_messages += ActiveModel.browse(res_id).message_post(**post_params)

                result_mails_su += batch_mails_sudo
                if wizard.composition_mode == 'mass_mail':
                    batch_mails_sudo.send(auto_commit=auto_commit)

        return result_mails_su, result_messages

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
            return _reopen(self, record.id, record.model, context=self._context)

    # ------------------------------------------------------------
    # RENDERING / VALUES GENERATION
    # ------------------------------------------------------------

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
        if mass_mail_mode and not self.reply_to_force_new:
            records = self.env[self.model].browse(res_ids)
            reply_to_value = records._notify_get_reply_to(default=False)
            # when having no specific reply-to, fetch rendered email_from value
            for res_id, reply_to in reply_to_value.items():
                if not reply_to:
                    reply_to_value[res_id] = rendered_values.get(res_id, {}).get('email_from', False)

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
                'reply_to_force_new': self.reply_to_force_new,
                'mail_server_id': self.mail_server_id.id,
                'mail_activity_type_id': self.mail_activity_type_id.id,
                'message_type': 'email' if mass_mail_mode else self.message_type,
            }

            # mass mailing: rendering override wizard static values
            if mass_mail_mode and self.model:
                record = self.env[self.model].browse(res_id)
                mail_values['headers'] = repr(record._notify_by_email_get_headers())
                # keep a copy unless specifically requested, reset record name (avoid browsing records)
                mail_values.update(is_notification=not self.auto_delete_message, model=self.model, res_id=res_id, record_name=False)
                # auto deletion of mail_mail
                if self.auto_delete or self.template_id.auto_delete:
                    mail_values['auto_delete'] = True
                # rendered values using template
                email_dict = rendered_values[res_id]
                mail_values['partner_ids'] += email_dict.pop('partner_ids', [])
                mail_values.update(email_dict)
                if not self.reply_to_force_new:
                    mail_values.pop('reply_to')
                    if reply_to_value.get(res_id):
                        mail_values['reply_to'] = reply_to_value[res_id]
                if self.reply_to_force_new and not mail_values.get('reply_to'):
                    mail_values['reply_to'] = mail_values['email_from']
                # mail_mail values: body -> body_html, partner_ids -> recipient_ids
                mail_values['body_html'] = mail_values.get('body', '')
                mail_values['recipient_ids'] = [Command.link(id) for id in mail_values.pop('partner_ids', [])]

                # process attachments: should not be encoded before being processed by message_post / mail_mail create
                mail_values['attachments'] = [(name, base64.b64decode(enc_cont)) for name, enc_cont in email_dict.pop('attachments', list())]
                attachment_ids = []
                for attach_id in mail_values.pop('attachment_ids'):
                    new_attach_id = self.env['ir.attachment'].browse(attach_id).copy({'res_model': self._name, 'res_id': self.id})
                    attachment_ids.append(new_attach_id.id)
                attachment_ids.reverse()
                mail_values['attachment_ids'] = self.env['mail.thread'].with_context(attached_to=record)._message_post_process_attachments(
                    mail_values.pop('attachments', []),
                    attachment_ids,
                    {'model': 'mail.message', 'res_id': 0}
                )['attachment_ids']

                # generate message_id directly; instead of letting mail_message create
                # method doing it. Then use it to craft references, allowing to keep
                # a trace of message_id even when email providers override it.
                # Note that if 'auto_delete' and 'auto_delete_message' are True,
                # mail.message is removed and parent finding based on messageID
                # may be broken, tough life
                message_id = self.env['mail.message']._get_message_id(mail_values)
                mail_values['message_id'] = message_id
                mail_values['references'] = message_id

            results[res_id] = mail_values

        results = self._process_state(results)
        return results

    def _process_recipient_values(self, mail_values_dict):
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

    def _process_state(self, mail_values_dict):
        recipients_info = self._process_recipient_values(mail_values_dict)
        blacklist_ids = self._get_blacklist_record_ids(mail_values_dict, recipients_info)
        optout_emails = [tools.email_normalize(email) for email in self._get_optout_emails(mail_values_dict)]
        done_emails = [tools.email_normalize(email) for email in self._get_done_emails(mail_values_dict)]
        # in case of an invoice e.g.
        mailing_document_based = self.env.context.get('mailing_document_based')

        for record_id, mail_values in mail_values_dict.items():
            recipients = recipients_info[record_id]

            # prevent sending to blocked addresses that were included by mistake
            # blacklisted or optout or duplicate -> cancel
            if record_id in blacklist_ids:
                mail_values['state'] = 'cancel'
                mail_values['failure_type'] = 'mail_bl'
                # Do not post the mail into the recipient's chatter
                mail_values['is_notification'] = False
            # void or falsy values -> error
            elif not any(recipients['mail_to']):
                mail_values['state'] = 'cancel'
                mail_values['failure_type'] = 'mail_email_missing'
            elif not any(recipients['mail_to_normalized']):
                mail_values['state'] = 'cancel'
                mail_values['failure_type'] = 'mail_email_invalid'
            elif optout_emails and all(
                    mail_to in optout_emails for mail_to in recipients['mail_to_normalized']
                ):
                mail_values['state'] = 'cancel'
                mail_values['failure_type'] = 'mail_optout'
            elif done_emails and not mailing_document_based and all(
                    mail_to in done_emails for mail_to in recipients['mail_to_normalized']
                ):
                mail_values['state'] = 'cancel'
                mail_values['failure_type'] = 'mail_dup'
            elif done_emails is not None and not mailing_document_based:
                done_emails.extend(recipients['mail_to_normalized'])

        return mail_values_dict

    def _get_blacklist_record_ids(self, mail_values_dict, recipients_info=None):
        """Get record ids for which at least one recipient is black listed.

        :param dict mail_values_dict: mail values per record id
        :param dict recipients_info: optional dict of recipients info per record id
            Optional for backward compatibility but without, result can be incomplete.
        :return set: record ids with at least one black listed recipient.
        """
        blacklisted_rec_ids = set()
        if self.composition_mode == 'mass_mail':
            self.env['mail.blacklist'].flush_model(['email', 'active'])
            self._cr.execute("SELECT email FROM mail_blacklist WHERE active=true")
            blacklist = {x[0] for x in self._cr.fetchall()}
            if not blacklist:
                return blacklisted_rec_ids
            if isinstance(self.env[self.model], self.pool['mail.thread.blacklist']):
                targets = self.env[self.model].browse(mail_values_dict.keys()).read(['email_normalized'])
                # First extract email from recipient before comparing with blacklist
                blacklisted_rec_ids.update(target['id'] for target in targets
                                           if target['email_normalized'] in blacklist)
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

    def _onchange_template_id(self, template_id, composition_mode, model, res_id):
        r""" - mass_mailing: we cannot render, so return the template values
            - normal mode: return rendered values
            /!\ for x2many field, this onchange return command instead of ids
        """
        if template_id and composition_mode == 'mass_mail':
            template = self.env['mail.template'].browse(template_id)
            values = dict(
                (field, template[field])
                for field in ['subject', 'body_html',
                              'email_from',
                              'reply_to',
                              'mail_server_id']
                if template[field]
            )
            if template.attachment_ids:
                values['attachment_ids'] = [att.id for att in template.attachment_ids]
            if template.mail_server_id:
                values['mail_server_id'] = template.mail_server_id.id
        elif template_id:
            values = self.generate_email_for_composer(
                template_id, [res_id],
                ['subject', 'body_html',
                 'email_from',
                 'email_cc', 'email_to', 'partner_to', 'reply_to',
                 'attachment_ids', 'mail_server_id'
                ]
            )[res_id]
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
                default_res_id=res_id
            ).default_get(['composition_mode', 'model', 'res_id', 'parent_id',
                           'subject', 'body',
                           'email_from',
                           'partner_ids', 'reply_to',
                           'attachment_ids', 'mail_server_id'
                          ])
            values = dict(
                (key, default_values[key])
                for key in ['subject', 'body',
                            'email_from',
                            'partner_ids', 'reply_to',
                            'attachment_ids', 'mail_server_id'
                           ] if key in default_values)

        if template_id:  # Restore default sender if not updated on template switch (for both "mass_mail" and "comment" modes)
            if 'email_from' not in values:
                values['email_from'] = self.default_get(['email_from']).get('email_from')

        if values.get('body_html'):
            values['body'] = values.pop('body_html')

        # This onchange should return command instead of ids for x2many field.
        values = self._convert_to_write(values)

        return {'value': values}

    def render_message(self, res_ids):
        """Generate template-based values of wizard, for the document records given
        by res_ids. This method is meant to be inherited by email_template that
        will produce a more complete dictionary, using qweb templates.

        Each template is generated for all res_ids, allowing to parse the template
        once, and render it multiple times. This is useful for mass mailing where
        template rendering represent a significant part of the process.

        Default recipients are also computed, based on mail_thread method
        _message_get_default_recipients. This allows to ensure a mass mailing has
        always some recipients specified.

        :param browse wizard: current mail.compose.message browse record
        :param list res_ids: list of record ids

        :return dict results: for each res_id, the generated template values for
                              subject, body, email_from and reply_to
        """
        self.ensure_one()
        multi_mode = True
        if isinstance(res_ids, int):
            multi_mode = False
            res_ids = [res_ids]

        subjects = self._render_field('subject', res_ids)
        # We want to preserve comments in emails so as to keep mso conditionals
        bodies = self._render_field('body', res_ids, post_process=True, options={'preserve_comments': self.composition_mode == 'mass_mail'})
        emails_from = self._render_field('email_from', res_ids)
        replies_to = self._render_field('reply_to', res_ids)
        default_recipients = {}
        if not self.partner_ids:
            records = self.env[self.model].browse(res_ids).sudo()
            default_recipients = records._message_get_default_recipients()

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
                ['email_to', 'partner_to', 'email_cc', 'attachment_ids', 'mail_server_id'])
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
    def generate_email_for_composer(self, template_id, res_ids, fields):
        """ Call email_template.generate_email(), get fields relevant for
            mail.compose.message, transform email_cc and email_to into partner_ids """
        multi_mode = True
        if isinstance(res_ids, int):
            multi_mode = False
            res_ids = [res_ids]

        returned_fields = fields + ['partner_ids', 'attachments']
        values = dict.fromkeys(res_ids, False)

        template_values = self.env['mail.template'].with_context(tpl_partners_only=True).browse(template_id).generate_email(res_ids, fields)
        for res_id in res_ids:
            res_id_values = dict((field, template_values[res_id][field]) for field in returned_fields if template_values[res_id].get(field))
            res_id_values['body'] = res_id_values.pop('body_html', '')
            values[res_id] = res_id_values

        return multi_mode and values or values[res_ids[0]]
