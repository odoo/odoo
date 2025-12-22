# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.osv import expression
from odoo.tools.mail import email_normalize, append_content_to_html

_logger = logging.getLogger(__name__)


class MailGroupMessage(models.Model):
    """Emails belonging to a discussion group.

    Those are build on <mail.message> with additional information related to specific
    features of <mail.group> like better parent / children management and moderation.
    """
    _name = 'mail.group.message'
    _description = 'Mailing List Message'
    _rec_name = 'subject'
    _order = 'create_date DESC'
    _primary_email = 'email_from'

    # <mail.message> fields, can not be done with inherits because it will impact
    # the performance of the <mail.message> model (different cache, so the ORM will need
    # to do one more SQL query to be able to update the <mail.group.message> cache)
    attachment_ids = fields.Many2many(related='mail_message_id.attachment_ids', readonly=False)
    author_id = fields.Many2one(related='mail_message_id.author_id', readonly=False)
    email_from = fields.Char(related='mail_message_id.email_from', readonly=False)
    email_from_normalized = fields.Char('Normalized From', compute='_compute_email_from_normalized', store=True)
    body = fields.Html(related='mail_message_id.body', readonly=False)
    subject = fields.Char(related='mail_message_id.subject', readonly=False)
    # Thread
    mail_group_id = fields.Many2one(
        'mail.group', string='Group',
        required=True, ondelete='cascade')
    mail_message_id = fields.Many2one('mail.message', 'Mail Message', required=True, ondelete='cascade', index=True, copy=False)
    # Parent and children
    group_message_parent_id = fields.Many2one(
        'mail.group.message', string='Parent', store=True)
    group_message_child_ids = fields.One2many('mail.group.message', 'group_message_parent_id', string='Children')
    # Moderation
    author_moderation = fields.Selection([('ban', 'Banned'), ('allow', 'Whitelisted')], string='Author Moderation Status',
                                         compute='_compute_author_moderation')
    is_group_moderated = fields.Boolean('Is Group Moderated', related='mail_group_id.moderation')
    moderation_status = fields.Selection(
        [('pending_moderation', 'Pending Moderation'),
         ('accepted', 'Accepted'),
         ('rejected', 'Rejected')],
        string='Status', index=True, copy=False,
        required=True, default='pending_moderation')
    moderator_id = fields.Many2one('res.users', string='Moderated By')
    create_date = fields.Datetime(string='Posted')

    @api.depends('email_from')
    def _compute_email_from_normalized(self):
        for message in self:
            message.email_from_normalized = email_normalize(message.email_from)

    @api.depends('email_from_normalized', 'mail_group_id')
    def _compute_author_moderation(self):
        moderations = self.env['mail.group.moderation'].search([
            ('mail_group_id', 'in', self.mail_group_id.ids),
        ])
        all_emails = set(self.mapped('email_from_normalized'))
        moderations = {
            (moderation.mail_group_id, moderation.email): moderation.status
            for moderation in moderations
            if moderation.email in all_emails
        }
        for message in self:
            message.author_moderation = moderations.get((message.mail_group_id, message.email_from_normalized), False)

    @api.constrains('mail_message_id')
    def _constrains_mail_message_id(self):
        for message in self:
            if message.mail_message_id.model != 'mail.group':
                raise AccessError(_(
                    'Group message can only be linked to mail group. Current model is %s.',
                    message.mail_message_id.model,
                ))
            if message.mail_message_id.res_id != message.mail_group_id.id:
                raise AccessError(_('The record of the message should be the group.'))

    @api.model_create_multi
    def create(self, values_list):
        for vals in values_list:
            if not vals.get('mail_message_id'):
                vals.update({
                    'res_id': vals.get('mail_group_id'),
                    'model': 'mail.group',
                })
                vals['mail_message_id'] = self.env['mail.message'].sudo().create({
                    field: vals.pop(field)
                    for field in self.env['mail.message']._fields
                    if field in vals
                    and field in self.env['mail.thread']._get_message_create_valid_field_names()
                }).id
        return super(MailGroupMessage, self).create(values_list)

    def copy_data(self, default=None):
        vals_list = super().copy_data(default)
        for message, vals in zip(self, vals_list):
            vals['mail_message_id'] = message.mail_message_id.copy().id
        return vals_list

    # --------------------------------------------------
    # MODERATION API
    # --------------------------------------------------

    def action_moderate_accept(self):
        """Accept the incoming email.

        Will send the incoming email to all members of the group.
        """
        self._assert_moderable()
        self.write({
            'moderation_status': 'accepted',
            'moderator_id': self.env.uid,
        })

        # Send the email to the members of the group
        for message in self:
            message.mail_group_id._notify_members(message)

    def action_moderate_reject_with_comment(self, reject_subject, reject_comment):
        self._assert_moderable()
        if reject_subject or reject_comment:
            self._moderate_send_reject_email(reject_subject, reject_comment)
        self.action_moderate_reject()

    def action_moderate_reject(self):
        self._assert_moderable()
        self.write({
            'moderation_status': 'rejected',
            'moderator_id': self.env.uid,
        })

    def action_moderate_allow(self):
        self._create_moderation_rule('allow')

        # Accept all emails of the same authors
        same_author = self._get_pending_same_author_same_group()
        same_author.action_moderate_accept()

    def action_moderate_ban(self):
        self._create_moderation_rule('ban')

        # Reject all emails of the same author
        same_author = self._get_pending_same_author_same_group()
        same_author.action_moderate_reject()

    def action_moderate_ban_with_comment(self, ban_subject, ban_comment):
        self._create_moderation_rule('ban')

        if ban_subject or ban_comment:
            self._moderate_send_reject_email(ban_subject, ban_comment)

        # Reject all emails of the same author
        same_author = self._get_pending_same_author_same_group()
        same_author.action_moderate_reject()

    def _get_pending_same_author_same_group(self):
        """Return the pending messages of the same authors in the same groups."""
        return self.search(
            expression.AND([
                expression.OR([
                    [
                        ('mail_group_id', '=', message.mail_group_id.id),
                        ('email_from_normalized', '=', message.email_from_normalized),
                    ] for message in self
                ]),
                [('moderation_status', '=', 'pending_moderation')],
            ])
        )

    def _create_moderation_rule(self, status):
        """Create a moderation rule <mail.group.moderation> with the given status.

        Update existing moderation rule for the same email address if found,
        otherwise create a new rule.
        """
        if status not in ('ban', 'allow'):
            raise ValueError(_('Wrong status (%s)', status))

        for message in self:
            if not email_normalize(message.email_from):
                raise UserError(_('The email "%s" is not valid.', message.email_from))

        existing_moderation = self.env['mail.group.moderation'].search(
            expression.OR([
                [
                    ('email', '=', email_normalize(message.email_from)),
                    ('mail_group_id', '=', message.mail_group_id.id)
                ] for message in self
            ])
        )
        existing_moderation.status = status

        # Add the value in a set to create only 1 moderation rule per (email_normalized, group)
        moderation_to_create = {
            (email_normalize(message.email_from), message.mail_group_id.id)
            for message in self
            if email_normalize(message.email_from) not in existing_moderation.mapped('email')
        }

        self.env['mail.group.moderation'].create([
            {
                'email': email,
                'mail_group_id': mail_group_id,
                'status': status,
            } for email, mail_group_id in moderation_to_create])

    def _assert_moderable(self):
        """Raise an error if one of the current message can not be moderated.

        A <mail.group.message> can only be moderated
        if it's moderation status is "pending_moderation".
        """
        non_moderable_messages = self.filtered_domain([
            ('moderation_status', '!=', 'pending_moderation'),
        ])
        if non_moderable_messages:
            if len(self) == 1:
                raise UserError(_('This message can not be moderated'))
            raise UserError(_(
                'Those messages can not be moderated: %s.',
                ', '.join(non_moderable_messages.mapped('subject')),
            ))

    def _moderate_send_reject_email(self, subject, comment):
        for message in self:
            if not message.email_from:
                continue

            body_html = append_content_to_html(Markup('<div>%s</div>') % comment, message.body, plaintext=False)
            body_html = self.env['mail.render.mixin']._replace_local_links(body_html)
            self.env['mail.mail'].sudo().create({
                'author_id': self.env.user.partner_id.id,
                'auto_delete': True,
                'body_html': body_html,
                'email_from': self.env.user.email_formatted or self.env.company.catchall_formatted,
                'email_to': message.email_from,
                'references': message.mail_message_id.message_id,
                'subject': subject,
                'state': 'outgoing',
            })
