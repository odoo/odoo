# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models, tools
from odoo.osv import expression


class Partner(models.Model):
    """ Update partner to add a field about notification preferences. Add a generic opt-out field that can be used
       to restrict usage of automatic email templates. """
    _name = "res.partner"
    _inherit = ['res.partner', 'mail.activity.mixin', 'mail.thread.blacklist']
    _mail_flat_thread = False

    # override to add and order tracking
    email = fields.Char(tracking=1)
    phone = fields.Char(tracking=2)
    parent_id = fields.Many2one(tracking=3)
    user_id = fields.Many2one(tracking=4)
    vat = fields.Char(tracking=5)
    # channels
    channel_ids = fields.Many2many('mail.channel', 'mail_channel_member', 'partner_id', 'channel_id', string='Channels', copy=False)

    def _compute_im_status(self):
        super()._compute_im_status()
        odoobot_id = self.env['ir.model.data']._xmlid_to_res_id('base.partner_root')
        odoobot = self.env['res.partner'].browse(odoobot_id)
        if odoobot in self:
            odoobot.im_status = 'bot'

    # pseudo computes

    def _get_needaction_count(self):
        """ compute the number of needaction of the current partner """
        self.ensure_one()
        self.env['mail.notification'].flush_model(['is_read', 'res_partner_id'])
        self.env.cr.execute("""
            SELECT count(*) as needaction_count
            FROM mail_notification R
            WHERE R.res_partner_id = %s AND (R.is_read = false OR R.is_read IS NULL)""", (self.id,))
        return self.env.cr.dictfetchall()[0].get('needaction_count')

    def _get_starred_count(self):
        """ compute the number of starred of the current partner """
        self.ensure_one()
        self.env.cr.execute("""
            SELECT count(*) as starred_count
            FROM mail_message_res_partner_starred_rel R
            WHERE R.res_partner_id = %s """, (self.id,))
        return self.env.cr.dictfetchall()[0].get('starred_count')

    # ------------------------------------------------------------
    # MESSAGING
    # ------------------------------------------------------------

    def _mail_get_partners(self):
        return dict((partner.id, partner) for partner in self)

    def _message_get_suggested_recipients(self):
        recipients = super(Partner, self)._message_get_suggested_recipients()
        for partner in self:
            partner._message_add_suggested_recipient(recipients, partner=partner, reason=_('Partner Profile'))
        return recipients

    def _message_get_default_recipients(self):
        return {
            r.id:
            {'partner_ids': [r.id],
             'email_to': False,
             'email_cc': False
            }
            for r in self
        }

    # ------------------------------------------------------------
    # ORM
    # ------------------------------------------------------------

    @api.model
    @api.returns('self', lambda value: value.id)
    def find_or_create(self, email, assert_valid_email=False):
        """ Override to use the email_normalized field. """
        if not email:
            raise ValueError(_('An email is required for find_or_create to work'))

        parsed_name, parsed_email = self._parse_partner_name(email)
        if not parsed_email and assert_valid_email:
            raise ValueError(_('%(email)s is not recognized as a valid email. This is required to create a new customer.'))
        if parsed_email:
            email_normalized = tools.email_normalize(parsed_email)
            if email_normalized:
                partners = self.search([('email_normalized', '=', email_normalized)], limit=1)
                if partners:
                    return partners

        # We don't want to call `super()` to avoid searching twice on the email
        # Especially when the search `email =ilike` cannot be as efficient as
        # a search on email_normalized with a btree index
        # If you want to override `find_or_create()` your module should depend on `mail`
        create_values = {self._rec_name: parsed_name or parsed_email}
        if parsed_email:  # otherwise keep default_email in context
            create_values['email'] = parsed_email
        return self.create(create_values)

    # ------------------------------------------------------------
    # DISCUSS
    # ------------------------------------------------------------

    def mail_partner_format(self, fields=None):
        partners_format = dict()
        if not fields:
            fields = {'id': True, 'name': True, 'email': True, 'active': True, 'im_status': True, 'user': {}}
        for partner in self:
            data = {}
            if 'id' in fields:
                data['id'] = partner.id
            if 'name' in fields:
                data['name'] = partner.name
            if 'email' in fields:
                data['email'] = partner.email
            if 'active' in fields:
                data['active'] = partner.active
            if 'im_status' in fields:
                data['im_status'] = partner.im_status
            if 'user' in fields:
                internal_users = partner.user_ids - partner.user_ids.filtered('share')
                main_user = internal_users[0] if len(internal_users) > 0 else partner.user_ids[0] if len(partner.user_ids) > 0 else self.env['res.users']
                data['user'] = {
                    "id": main_user.id,
                    "isInternalUser": not main_user.share,
                } if main_user else [('clear',)]
            if 'guest' in self.env.context:
                data.pop('email')
            partners_format[partner] = data
        return partners_format

    def _message_fetch_failed(self):
        """Returns first 100 messages, sent by the current partner, that have errors, in
        the format expected by the web client."""
        self.ensure_one()
        notifications = self.env['mail.notification'].search([
            ('author_id', '=', self.id),
            ('notification_status', 'in', ('bounce', 'exception')),
            ('mail_message_id.message_type', '!=', 'user_notification'),
            ('mail_message_id.model', '!=', False),
            ('mail_message_id.res_id', '!=', 0),
        ], limit=100)
        return notifications.mail_message_id._message_notification_format()

    def _get_channels_as_member(self):
        """Returns the channels of the partner."""
        self.ensure_one()
        channels = self.env['mail.channel']
        # get the channels and groups
        channels |= self.env['mail.channel'].search([
            ('channel_type', 'in', ('channel', 'group')),
            ('channel_partner_ids', 'in', [self.id]),
        ])
        # get the pinned direct messages
        channels |= self.env['mail.channel'].search([
            ('channel_type', '=', 'chat'),
            ('channel_member_ids', 'in', self.env['mail.channel.member'].sudo()._search([
                ('partner_id', '=', self.id),
                ('is_pinned', '=', True),
            ])),
        ])
        return channels

    @api.model
    def search_for_channel_invite(self, search_term, channel_id=None, limit=30):
        """ Returns partners matching search_term that can be invited to a channel.
        If the channel_id is specified, only partners that can actually be invited to the channel
        are returned (not already members, and in accordance to the channel configuration).
        """
        domain = expression.AND([
            expression.OR([
                [('name', 'ilike', search_term)],
                [('email', 'ilike', search_term)],
            ]),
            [('active', '=', True)],
            [('type', '!=', 'private')],
            [('user_ids', '!=', False)],
            [('user_ids.active', '=', True)],
            [('user_ids.share', '=', False)],
        ])
        if channel_id:
            channel = self.env['mail.channel'].search([('id', '=', int(channel_id))])
            domain = expression.AND([domain, [('channel_ids', 'not in', channel.id)]])
            if channel.public == 'groups':
                domain = expression.AND([domain, [('user_ids.groups_id', 'in', channel.group_public_id.id)]])
        query = self.env['res.partner']._search(domain, order='name, id')
        query.order = 'LOWER("res_partner"."name"), "res_partner"."id"'  # bypass lack of support for case insensitive order in search()
        query.limit = int(limit)
        return {
            'count': self.env['res.partner'].search_count(domain),
            'partners': list(self.env['res.partner'].browse(query).mail_partner_format().values()),
        }

    @api.model
    def get_mention_suggestions(self, search, limit=8, channel_id=None):
        """ Return 'limit'-first partners' such that the name or email matches a 'search' string.
            Prioritize partners that are also (internal) users, and then extend the research to all partners.
            If channel_id is given, only members of this channel are returned.
            The return format is a list of partner data (as per returned by `mail_partner_format()`).
        """
        search_dom = expression.OR([[('name', 'ilike', search)], [('email', 'ilike', search)]])
        search_dom = expression.AND([[('active', '=', True), ('type', '!=', 'private')], search_dom])
        if channel_id:
            search_dom = expression.AND([[('channel_ids', 'in', channel_id)], search_dom])
        domain_is_user = expression.AND([[('user_ids', '!=', False), ('user_ids.active', '=', True)], search_dom])
        priority_conditions = [
            expression.AND([domain_is_user, [('partner_share', '=', False)]]),  # Search partners that are internal users
            domain_is_user,  # Search partners that are users
            search_dom,  # Search partners that are not users
        ]
        partners = self.env['res.partner']
        for domain in priority_conditions:
            remaining_limit = limit - len(partners)
            if remaining_limit <= 0:
                break
            partners |= self.search(expression.AND([[('id', 'not in', partners.ids)], domain]), limit=remaining_limit)
        partners_format = partners.mail_partner_format()
        if channel_id:
            member_by_partner = {member.partner_id: member for member in self.env['mail.channel.member'].search([('channel_id', '=', channel_id), ('partner_id', 'in', partners.ids)])}
            for partner in partners:
                partners_format.get(partner)['persona'] = {
                    'channelMembers': [('insert', member_by_partner.get(partner)._mail_channel_member_format(fields={'id': True, 'channel': {'id'}, 'persona': {'partner': {'id'}}}).get(member_by_partner.get(partner)))],
                }
        return list(partners_format.values())

    @api.model
    def im_search(self, name, limit=20):
        """ Search partner with a name and return its id, name and im_status.
            Note : the user must be logged
            :param name : the partner name to search
            :param limit : the limit of result to return
        """
        # This method is supposed to be used only in the context of channel creation or
        # extension via an invite. As both of these actions require the 'create' access
        # right, we check this specific ACL.
        users = self.env['res.users'].search([
            ('id', '!=', self.env.user.id),
            ('name', 'ilike', name),
            ('active', '=', True),
            ('share', '=', False),
        ], order='name, id', limit=limit)
        return list(users.partner_id.mail_partner_format().values())
