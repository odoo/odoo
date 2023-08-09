# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import lxml

from ast import literal_eval
from datetime import datetime
from dateutil import relativedelta
from werkzeug import urls

from odoo import _, api, fields, models, tools
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.mail.tools.alias_error import AliasError
from odoo.exceptions import ValidationError, UserError
from odoo.osv import expression
from odoo.tools import email_normalize, hmac, generate_tracking_message_id

_logger = logging.getLogger(__name__)

# TODO remove me master
GROUP_SEND_BATCH_SIZE = 500


class MailGroup(models.Model):
    """This model represents a mailing list.

    Users send emails to an alias to create new group messages or reply to existing
    group messages. Moderation can be activated on groups. In that case email have to
    be validated or rejected.
    """
    _name = 'mail.group'
    _description = 'Mail Group'
    # TDE CHECK: use blaclist mixin
    _inherit = ['mail.alias.mixin']
    _order = 'create_date DESC, id DESC'

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if 'alias_contact' in fields and not res.get('alias_contact'):
            res['alias_contact'] = 'everyone' if res.get('access_mode') == 'public' else 'followers'
        return res

    active = fields.Boolean('Active', default=True)
    name = fields.Char('Name', required=True, translate=True)
    description = fields.Text('Description')
    image_128 = fields.Image('Image', max_width=128, max_height=128)
    # Messages
    mail_group_message_ids = fields.One2many('mail.group.message', 'mail_group_id', string='Pending Messages')
    mail_group_message_last_month_count = fields.Integer('Messages Per Month', compute='_compute_mail_group_message_last_month_count')
    mail_group_message_count = fields.Integer('Messages Count', help='Number of message in this group', compute='_compute_mail_group_message_count')
    mail_group_message_moderation_count = fields.Integer('Pending Messages Count', help='Messages that need an action', compute='_compute_mail_group_message_moderation_count')
    # Members
    is_member = fields.Boolean('Is Member', compute='_compute_is_member')
    member_ids = fields.One2many('mail.group.member', 'mail_group_id', string='Members')
    member_partner_ids = fields.Many2many('res.partner', string='Partners Member', compute='_compute_member_partner_ids', search='_search_member_partner_ids')
    member_count = fields.Integer('Members Count', compute='_compute_member_count')
    # Moderation
    is_moderator = fields.Boolean(string='Moderator', help='Current user is a moderator of the group', compute='_compute_is_moderator')
    moderation = fields.Boolean(string='Moderate this group')
    moderation_rule_count = fields.Integer(string='Moderated emails count', compute='_compute_moderation_rule_count')
    moderation_rule_ids = fields.One2many('mail.group.moderation', 'mail_group_id', string='Moderated Emails')
    moderator_ids = fields.Many2many('res.users', 'mail_group_moderator_rel', string='Moderators',
                                     domain=lambda self: [('groups_id', 'in', self.env.ref('base.group_user').id)])
    moderation_notify = fields.Boolean(
        string='Automatic notification',
        help='People receive an automatic notification about their message being waiting for moderation.')
    moderation_notify_msg = fields.Html(string='Notification message')
    moderation_guidelines = fields.Boolean(
        string='Send guidelines to new subscribers',
        help='Newcomers on this moderated group will automatically receive the guidelines.')
    moderation_guidelines_msg = fields.Html(string='Guidelines')
    # ACLs
    access_mode = fields.Selection([
        ('public', 'Everyone'),
        ('members', 'Members only'),
        ('groups', 'Selected group of users'),
        ], string='Privacy', required=True, default='public')
    access_group_id = fields.Many2one('res.groups', string='Authorized Group',
                                      default=lambda self: self.env.ref('base.group_user'))
    # UI
    can_manage_group = fields.Boolean('Can Manage', help='Can manage the members', compute='_compute_can_manage_group')

    @api.depends('mail_group_message_ids.create_date', 'mail_group_message_ids.moderation_status')
    def _compute_mail_group_message_last_month_count(self):
        month_date = datetime.today() - relativedelta.relativedelta(months=1)
        messages_data = self.env['mail.group.message']._read_group([
            ('mail_group_id', 'in', self.ids),
            ('create_date', '>=', fields.Datetime.to_string(month_date)),
            ('moderation_status', '=', 'accepted'),
        ], ['mail_group_id'], ['__count'])

        # { mail_discusison_id: number_of_mail_group_message_last_month_count }
        messages_data = {
            mail_group.id: count
            for mail_group, count in messages_data
        }

        for group in self:
            group.mail_group_message_last_month_count = messages_data.get(group.id, 0)

    @api.depends('mail_group_message_ids')
    def _compute_mail_group_message_count(self):
        if not self:
            self.mail_group_message_count = 0
            return

        results = self.env['mail.group.message']._read_group(
            [('mail_group_id', 'in', self.ids)],
            ['mail_group_id'],
            ['__count'],
        )
        result_per_group = {
            mail_group.id: count
            for mail_group, count in results
        }
        for group in self:
            group.mail_group_message_count = result_per_group.get(group.id, 0)

    @api.depends('mail_group_message_ids.moderation_status')
    def _compute_mail_group_message_moderation_count(self):
        results = self.env['mail.group.message']._read_group(
            [('mail_group_id', 'in', self.ids), ('moderation_status', '=', 'pending_moderation')],
            ['mail_group_id'],
            ['__count'],
        )
        result_per_group = {
            mail_group.id: count
            for mail_group, count in results
        }

        for group in self:
            group.mail_group_message_moderation_count = result_per_group.get(group.id, 0)

    @api.depends('member_ids')
    def _compute_member_count(self):
        for group in self:
            group.member_count = len(group.member_ids)

    @api.depends_context('uid')
    def _compute_is_member(self):
        if not self or self.env.user._is_public():
            self.is_member = False
            return

        # SUDO to bypass the ACL rules
        members = self.env['mail.group.member'].sudo().search([
            ('partner_id', '=', self.env.user.partner_id.id),
            ('mail_group_id', 'in', self.ids),
        ])
        is_member = {member.mail_group_id.id: True for member in members}

        for group in self:
            group.is_member = is_member.get(group.id, False)

    @api.depends('member_ids')
    def _compute_member_partner_ids(self):
        for group in self:
            group.member_partner_ids = group.member_ids.partner_id

    def _search_member_partner_ids(self, operator, operand):
        return [(
            'member_ids',
            'in',
            self.env['mail.group.member'].sudo()._search([
                ('partner_id', operator, operand)
            ])
        )]

    @api.depends('moderator_ids')
    @api.depends_context('uid')
    def _compute_is_moderator(self):
        for group in self:
            group.is_moderator = self.env.user.id in group.moderator_ids.ids

    @api.depends('moderation_rule_ids')
    def _compute_moderation_rule_count(self):
        for group in self:
            group.moderation_rule_count = len(group.moderation_rule_ids)

    @api.depends('is_moderator')
    @api.depends_context('uid')
    def _compute_can_manage_group(self):
        is_admin = self.env.user.has_group('mail_group.group_mail_group_manager') or self.env.su
        for group in self:
            group.can_manage_group = is_admin or group.is_moderator

    @api.onchange('access_mode')
    def _onchange_access_mode(self):
        if self.access_mode == 'public':
            self.alias_contact = 'everyone'
        else:
            self.alias_contact = 'followers'

    @api.onchange('moderation')
    def _onchange_moderation(self):
        if self.moderation and self.env.user not in self.moderator_ids:
            self.moderator_ids |= self.env.user

    # CONSTRAINTS

    @api.constrains('moderator_ids')
    def _check_moderator_email(self):
        if any(not moderator.email for group in self for moderator in group.moderator_ids):
            raise ValidationError(_('Moderators must have an email address.'))

    @api.constrains('moderation_notify', 'moderation_notify_msg')
    def _check_moderation_notify(self):
        if any(group.moderation_notify and not group.moderation_notify_msg for group in self):
            raise ValidationError(_('The notification message is missing.'))

    @api.constrains('moderation_guidelines', 'moderation_guidelines_msg')
    def _check_moderation_guidelines(self):
        if any(group.moderation_guidelines and not group.moderation_guidelines_msg for group in self):
            raise ValidationError(_('The guidelines description is missing.'))

    @api.constrains('moderator_ids', 'moderation')
    def _check_moderator_existence(self):
        if any(not group.moderator_ids for group in self if group.moderation):
            raise ValidationError(_('Moderated group must have moderators.'))

    @api.constrains('access_mode', 'access_group_id')
    def _check_access_mode(self):
        if any(group.access_mode == 'groups' and not group.access_group_id for group in self):
            raise ValidationError(_('The "Authorized Group" is missing.'))

    def _alias_get_creation_values(self):
        """Return the default values for the automatically created alias."""
        values = super(MailGroup, self)._alias_get_creation_values()
        values['alias_model_id'] = self.env['ir.model']._get('mail.group').id
        values['alias_force_thread_id'] = self.id
        values['alias_defaults'] = literal_eval(self.alias_defaults or '{}')
        return values

    # ------------------------------------------------------------
    # MAILING
    # ------------------------------------------------------------

    def _alias_get_error(self, message, message_dict, alias):
        self.ensure_one()

        if alias.alias_contact == 'followers':
            # Members only
            if not self._find_member(message_dict.get('email_from')):
                return AliasError('error_mail_group_members_restricted',
                                  _('Only members can send email to the mailing list.'))
            # Skip the verification because the partner is in the member list
            return

        return super(MailGroup, self)._alias_get_error(message, message_dict, alias)

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """Add the method to make the mail gateway flow work with this model."""
        return

    @api.model
    def message_update(self, msg_dict, update_vals=None):
        """Add the method to make the mail gateway flow work with this model."""
        return

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, body='', subject=None, email_from=None, author_id=None, **kwargs):
        """ Custom posting process. This model does not inherit from ``mail.thread``
        but uses the mail gateway so few methods should be defined.

        This custom posting process works as follow

          * create a ``mail.message`` based on incoming email;
          * create linked ``mail.group.message`` that encapsulates message in a
            format used in mail groups;
          * apply moderation rules;

        :return message: newly-created mail.message
        """
        self.ensure_one()
        # First create the <mail.message>
        Mailthread = self.env['mail.thread']
        values = dict((key, val) for key, val in kwargs.items() if key in self.env['mail.message']._fields)
        author_id, email_from = Mailthread._message_compute_author(author_id, email_from, raise_on_email=True)

        values.update({
            'author_id': author_id,
            'body': self._clean_email_body(body),
            'email_from': email_from,
            'model': self._name,
            'partner_ids': [],
            'res_id': self.id,
            'subject': subject,
        })

        # Force the "reply-to" to make the mail group flow work
        values['reply_to'] = self.env['mail.message']._get_reply_to(values)

        # ensure message ID so that replies go to the right thread
        if not values.get('message_id'):
            values['message_id'] = generate_tracking_message_id('%s-mail.group' % self.id)

        values.update(Mailthread._process_attachments_for_post(
            kwargs.get('attachments') or [],
            kwargs.get('attachment_ids') or [],
            values
        ))

        mail_message = Mailthread._message_create([values])

        # Find the <mail.group.message> parent
        group_message_parent_id = False
        if mail_message.parent_id:
            group_message_parent = self.env['mail.group.message'].search(
                [('mail_message_id', '=', mail_message.parent_id.id)])
            group_message_parent_id = group_message_parent.id if group_message_parent else False

        moderation_status = 'pending_moderation' if self.moderation else 'accepted'

        # Create the group message associated
        group_message = self.env['mail.group.message'].create({
            'mail_group_id': self.id,
            'mail_message_id': mail_message.id,
            'moderation_status': moderation_status,
            'group_message_parent_id': group_message_parent_id,
        })

        # Check the moderation rule to determine if we should accept or reject the email
        email_normalized = email_normalize(email_from)
        moderation_rule = self.env['mail.group.moderation'].search([
            ('mail_group_id', '=', self.id),
            ('email', '=', email_normalized),
        ], limit=1)

        if not self.moderation:
            self._notify_members(group_message)

        elif moderation_rule and moderation_rule.status == 'allow':
            group_message.action_moderate_accept()

        elif moderation_rule and moderation_rule.status == 'ban':
            group_message.action_moderate_reject()

        elif self.moderation_notify:
            self.env['mail.mail'].sudo().create({
                'author_id': self.env.user.partner_id.id,
                'auto_delete': True,
                'body_html': group_message.mail_group_id.moderation_notify_msg,
                'email_from': self.env.user.company_id.catchall_formatted or self.env.user.company_id.email_formatted,
                'email_to': email_from,
                'subject': 'Re: %s' % (subject or ''),
                'state': 'outgoing'
            })

        return mail_message

    def action_send_guidelines(self, members=None):
        """ Send guidelines to given members. """
        self.ensure_one()

        if not self.env.is_admin() and not self.is_moderator:
            raise UserError(_('Only an administrator or a moderator can send guidelines to group members.'))

        if not self.moderation_guidelines_msg:
            raise UserError(_('The guidelines description is empty.'))

        template = self.env.ref('mail_group.mail_template_guidelines', raise_if_not_found=False)
        if not template:
            raise UserError(_('Template "mail_group.mail_template_guidelines" was not found. No email has been sent. Please contact an administrator to fix this issue.'))

        banned_emails = self.env['mail.group.moderation'].sudo().search([
            ('status', '=', 'ban'),
            ('mail_group_id', '=', self.id),
        ]).mapped('email')

        if members is None:
            members = self.member_ids
        members = members.filtered(lambda member: member.email_normalized not in banned_emails)

        for member in members:
            company = member.partner_id.company_id or self.env.company
            template.send_mail(
                member.id,
                email_values={
                    'author_id': self.env.user.partner_id.id,
                    'email_from': company.email_formatted or company.catchall_formatted,
                    'reply_to': company.email_formatted or company.catchall_formatted,
                },
            )

        _logger.info('Send guidelines to %i members', len(members))

    def _notify_members(self, message):
        """Send the given message to all members of the mail group (except the author)."""
        self.ensure_one()

        if message.mail_group_id != self:
            raise UserError(_('The group of the message do not match.'))

        if not message.mail_message_id.reply_to:
            _logger.error('The alias or the catchall domain is missing, group might not work properly.')

        base_url = self.get_base_url()
        body = self.env['mail.render.mixin']._replace_local_links(message.body)
        access_token = self._generate_group_access_token()

        # Email added in a dict to be sure to send only once the email to each address
        member_emails = {
            email_normalize(member.email): member.email
            for member in self.member_ids
        }

        batch_size = int(self.env['ir.config_parameter'].sudo().get_param('mail.session.batch.size', GROUP_SEND_BATCH_SIZE))
        for batch_email_member in tools.split_every(batch_size, member_emails.items()):
            mail_values = []
            for email_member_normalized, email_member in batch_email_member:
                if email_member_normalized == message.email_from_normalized:
                    # Do not send the email to their author
                    continue

                # SMTP headers related to the subscription
                email_url_encoded = urls.url_quote(email_member)
                headers = {
                    ** self._notify_by_email_get_headers(),
                    'List-Archive': f'<{base_url}/groups/{slug(self)}>',
                    'List-Subscribe': f'<{base_url}/groups?email={email_url_encoded}>',
                    'List-Unsubscribe': f'<{base_url}/groups?unsubscribe&email={email_url_encoded}>',
                    'Precedence': 'list',
                    'X-Auto-Response-Suppress': 'OOF',  # avoid out-of-office replies from MS Exchange
                }
                if self.alias_email:
                    headers.update({
                        'List-Id': f'<{self.alias_email}>',
                        'List-Post': f'<mailto:{self.alias_email}>',
                        'X-Forge-To': f'"{self.name}" <{self.alias_email}>',
                    })

                if message.mail_message_id.parent_id:
                    headers['In-Reply-To'] = message.mail_message_id.parent_id.message_id

                # Add the footer (member specific) in the body
                template_values = {
                    'mailto': f'{self.alias_email}',
                    'group_url': f'{base_url}/groups/{slug(self)}',
                    'unsub_label': f'{base_url}/groups?unsubscribe',
                    'unsub_url':  f'{base_url}/groups?unsubscribe&group_id={self.id}&token={access_token}&email={email_url_encoded}',
                }
                footer = self.env['ir.qweb']._render('mail_group.mail_group_footer', template_values, minimal_qcontext=True)
                member_body = tools.append_content_to_html(body, footer, plaintext=False)

                mail_values.append({
                    'auto_delete': True,
                    'attachment_ids': message.attachment_ids.ids,
                    'body_html': member_body,
                    'email_from': message.email_from,
                    'email_to': email_member,
                    'headers': json.dumps(headers),
                    'mail_message_id': message.mail_message_id.id,
                    'message_id': message.mail_message_id.message_id,
                    'model': 'mail.group',
                    'reply_to': message.mail_message_id.reply_to,
                    'res_id': self.id,
                    'subject': message.subject,
                })

            if mail_values:
                self.env['mail.mail'].sudo().create(mail_values)

    @api.model
    def _cron_notify_moderators(self):
        moderated_groups = self.env['mail.group'].search([('moderation', '=', True)])
        return moderated_groups._notify_moderators()

    def _notify_moderators(self):
        """Push a notification (Inbox / Email) to the moderators whose an action is waiting."""
        template = self.env.ref('mail_group.mail_group_notify_moderation', raise_if_not_found=False)
        if not template:
            _logger.warning('Template "mail_group.mail_group_notify_moderation" was not found. Cannot send reminder notifications.')
            return

        results = self.env['mail.group.message']._read_group(
            [('mail_group_id', 'in', self.ids), ('moderation_status', '=', 'pending_moderation')],
            ['mail_group_id'],
        )
        groups = self.browse([mail_group.id for [mail_group] in results])

        for group in groups:
            moderators_to_notify = group.moderator_ids
            MailThread = self.env['mail.thread']
            for moderator in moderators_to_notify:
                body = self.env['ir.qweb']._render('mail_group.mail_group_notify_moderation', {
                    'moderator': moderator,
                    'group': group,
                    }, minimal_qcontext=True)
                email_from = moderator.company_id.catchall_formatted or moderator.company_id.email_formatted
                MailThread.message_notify(
                    partner_ids=moderator.partner_id.ids,
                    subject=_('Messages are pending moderation'),
                    body=body,
                    email_from=email_from,
                    model='mail.group',
                    notify_author=True,
                    res_id=group.id,
                )

    @api.model
    def _clean_email_body(self, body_html):
        """When we receive an email, we want to clean it before storing it in the database."""
        tree = lxml.html.fromstring(body_html or '')
        # Remove the mailing footer
        xpath_footer = ".//div[contains(@id, 'o_mg_message_footer')]"
        for parent_footer in tree.xpath(xpath_footer + "/.."):
            for footer in parent_footer.xpath(xpath_footer):
                parent_footer.remove(footer)

        return lxml.etree.tostring(tree, encoding='utf-8').decode()

    # ------------------------------------------------------------
    # MEMBERSHIP
    # ------------------------------------------------------------

    def action_join(self):
        self.check_access_rights('read')
        self.check_access_rule('read')
        partner = self.env.user.partner_id
        self.sudo()._join_group(partner.email, partner.id)

        _logger.info('"%s" (#%s) joined mail.group "%s" (#%s)', partner.name, partner.id, self.name, self.id)

    def action_leave(self):
        self.check_access_rights('read')
        self.check_access_rule('read')
        partner = self.env.user.partner_id
        self.sudo()._leave_group(partner.email, partner.id)

        _logger.info('"%s" (#%s) leaved mail.group "%s" (#%s)', partner.name, partner.id, self.name, self.id)

    def _join_group(self, email, partner_id=None):
        self.ensure_one()

        if partner_id:
            partner = self.env['res.partner'].browse(partner_id).exists()
            if not partner:
                raise ValidationError(_('The partner can not be found.'))
            email = partner.email

        existing_member = self._find_member(email, partner_id)
        if existing_member:
            # Update the information of the partner to force the synchronization
            # If one the value is not up to date (e.g. if our email is subscribed
            # but our partner was not set)
            existing_member.write({
                'email': email,
                'partner_id': partner_id,
            })
            return

        member = self.env['mail.group.member'].create({
            'partner_id': partner_id,
            'email': email,
            'mail_group_id': self.id,
        })

        if self.moderation_guidelines:
            # Automatically send the guidelines to the new member
            self.action_send_guidelines(member)

    def _leave_group(self, email, partner_id=None, all_members=False):
        """Remove the given email / partner from the group.

        If the "all_members" parameter is set to True, remove all members with the given
        email address (multiple members might have the same email address).

        Otherwise, remove the most appropriate.
        """
        self.ensure_one()
        if all_members and not partner_id:
            self.env['mail.group.member'].search([
                ('mail_group_id', '=', self.id),
                ('email_normalized', '=', email_normalize(email)),
            ]).unlink()
        else:
            member = self._find_member(email, partner_id)
            if member:
                member.unlink()

    def _send_subscribe_confirmation_email(self, email):
        """Send an email to the given address to subscribe / unsubscribe to the mailing list."""
        self.ensure_one()
        confirm_action_url = self._generate_action_url(email, 'subscribe')

        template = self.env.ref('mail_group.mail_template_list_subscribe')
        template.with_context(token_url=confirm_action_url).send_mail(
            self.id,
            email_layout_xmlid='mail.mail_notification_light',
            email_values={
                'author_id': self.create_uid.partner_id.id,
                'auto_delete': True,
                'email_from': self.env.company.email_formatted,
                'email_to': email,
                'message_type': 'user_notification',
            },
            force_send=True,
        )
        _logger.info('Subscription email sent to %s.', email)

    def _send_unsubscribe_confirmation_email(self, email):
        """Send an email to the given address to subscribe / unsubscribe to the mailing list."""
        self.ensure_one()
        confirm_action_url = self._generate_action_url(email, 'unsubscribe')

        template = self.env.ref('mail_group.mail_template_list_unsubscribe')
        template.with_context(token_url=confirm_action_url).send_mail(
            self.id,
            email_layout_xmlid='mail.mail_notification_light',
            email_values={
                'author_id': self.create_uid.partner_id.id,
                'auto_delete': True,
                'email_from': self.env.company.email_formatted,
                'email_to': email,
                'message_type': 'user_notification',
            },
            force_send=True,
        )
        _logger.info('Unsubscription email sent to %s.', email)

    def _generate_action_url(self, email, action):
        """Generate the confirmation URL to subscribe / unsubscribe from the mailing list."""
        if action not in ['subscribe', 'unsubscribe']:
            raise ValueError(_('Invalid action for URL generation (%s)', action))
        self.ensure_one()

        confirm_action_url = '/group/%s-confirm?%s' % (
            action,
            urls.url_encode({
                'group_id': self.id,
                'email': email,
                'token': self._generate_action_token(email, action),
            })
        )
        base_url = self.get_base_url()
        confirm_action_url = urls.url_join(base_url, confirm_action_url)
        return confirm_action_url

    def _generate_action_token(self, email, action):
        """Generate an action token to be able to subscribe / unsubscribe from the mailing list."""
        if action not in ['subscribe', 'unsubscribe']:
            raise ValueError(_('Invalid action for URL generation (%s)', action))
        self.ensure_one()

        email_normalized = email_normalize(email)
        if not email_normalized:
            raise UserError(_('Email %s is invalid', email))

        data = (self.id, email_normalized, action)
        return hmac(self.env(su=True), 'mail_group-email-subscription', data)

    def _generate_group_access_token(self):
        """Generate an action token to be able to subscribe / unsubscribe from the mailing list."""
        self.ensure_one()
        return hmac(self.env(su=True), 'mail_group-access-token-portal', self.id)

    def _find_member(self, email, partner_id=None):
        """Return the <mail.group.member> corresponding to the given email address."""
        self.ensure_one()

        result = self._find_members(email, partner_id)
        return result.get(self.id)

    def _find_members(self, email, partner_id):
        """Get all the members record corresponding to the email / partner_id.

        Can be called in batch and return a dictionary
            {'group_id': <mail.group.member>}

        Multiple members might have the same email address, but with different partner
        because there's no unique constraint on the email field of the <res.partner>
        model.

        When a partner is given for the search, return in priority
        - The member whose partner match the given partner
        - The member without partner but whose email match the given email

        When no partner is given for the search, return in priority
        - A member whose email match the given email and has no partner
        - A member whose email match the given email and has partner
        """
        order = 'partner_id ASC'
        if not email_normalize(email):
            # empty email should match nobody
            return {}

        domain = [('email_normalized', '=', email_normalize(email))]
        if partner_id:
            domain = expression.OR([
                expression.AND([
                    [('partner_id', '=', False)],
                    domain,
                ]),
                [('partner_id', '=', partner_id)],
            ])
            order = 'partner_id DESC'

        domain = expression.AND([domain, [('mail_group_id', 'in', self.ids)]])
        members_data = self.env['mail.group.member'].sudo().search(domain, order=order)
        return {
            member.mail_group_id.id: member
            for member in members_data
        }
