# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, fields, models, tools
from odoo.addons.bus.models.bus_presence import AWAY_TIMER
from odoo.addons.bus.models.bus_presence import DISCONNECTION_TIMER
from odoo.exceptions import AccessError
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    """ Update partner to add a field about notification preferences. Add a generic opt-out field that can be used
       to restrict usage of automatic email templates. """
    _name = "res.partner"
    _inherit = ['res.partner', 'mail.activity.mixin', 'mail.thread.blacklist']
    _mail_flat_thread = False

    email = fields.Char(tracking=1)
    phone = fields.Char(tracking=2)

    channel_ids = fields.Many2many('mail.channel', 'mail_channel_partner', 'partner_id', 'channel_id', string='Channels', copy=False)
    # override the field to track the visibility of user
    user_id = fields.Many2one(tracking=True)

    def _compute_im_status(self):
        super()._compute_im_status()
        odoobot_id = self.env['ir.model.data'].xmlid_to_res_id('base.partner_root')
        odoobot = self.env['res.partner'].browse(odoobot_id)
        if odoobot in self:
            odoobot.im_status = 'bot'

    def _message_get_suggested_recipients(self):
        recipients = super(Partner, self)._message_get_suggested_recipients()
        for partner in self:
            partner._message_add_suggested_recipient(recipients, partner=partner, reason=_('Partner Profile'))
        return recipients

    def _message_get_default_recipients(self):
        return {r.id: {
            'partner_ids': [r.id],
            'email_to': False,
            'email_cc': False}
            for r in self}

    @api.model
    @api.returns('self', lambda value: value.id)
    def find_or_create(self, email, assert_valid_email=False):
        """ Override to use the email_normalized field. """
        if not email:
            raise ValueError(_('An email is required for find_or_create to work'))

        parsed_name, parsed_email = self._parse_partner_name(email)
        if parsed_email:
            email_normalized = tools.email_normalize(parsed_email)
            if email_normalized:
                partners = self.search([('email_normalized', '=', email_normalized)], limit=1)
                if partners:
                    return partners

        return super(Partner, self).find_or_create(email, assert_valid_email=assert_valid_email)

    def mail_partner_format(self):
        self.ensure_one()
        internal_users = self.user_ids - self.user_ids.filtered('share')
        main_user = internal_users[0] if len(internal_users) else self.user_ids[0] if len(self.user_ids) else self.env['res.users']
        res = {
            "id": self.id,
            "display_name": self.display_name,
            "name": self.name,
            "email": self.email,
            "active": self.active,
            "im_status": self.im_status,
            "user_id": main_user.id,
        }
        if main_user:
            res["is_internal_user"] = not main_user.share
        return res

    @api.model
    def get_needaction_count(self):
        """ compute the number of needaction of the current user """
        if self.env.user.partner_id:
            self.env['mail.notification'].flush(['is_read', 'res_partner_id'])
            self.env.cr.execute("""
                SELECT count(*) as needaction_count
                FROM mail_message_res_partner_needaction_rel R
                WHERE R.res_partner_id = %s AND (R.is_read = false OR R.is_read IS NULL)""", (self.env.user.partner_id.id,))
            return self.env.cr.dictfetchall()[0].get('needaction_count')
        _logger.error('Call to needaction_count without partner_id')
        return 0

    @api.model
    def get_starred_count(self):
        """ compute the number of starred of the current user """
        if self.env.user.partner_id:
            self.env.cr.execute("""
                SELECT count(*) as starred_count
                FROM mail_message_res_partner_starred_rel R
                WHERE R.res_partner_id = %s """, (self.env.user.partner_id.id,))
            return self.env.cr.dictfetchall()[0].get('starred_count')
        _logger.error('Call to starred_count without partner_id')
        return 0

    @api.model
    def get_static_mention_suggestions(self):
        """Returns static mention suggestions of partners, loaded once at
        webclient initialization and stored client side.
        By default all the internal users are returned.

        The return format is a list of lists. The first level of list is an
        arbitrary split that allows overrides to return their own list.
        The second level of list is a list of partner data (as per returned by
        `mail_partner_format()`).
        """
        suggestions = []
        try:
            suggestions.append([partner.mail_partner_format() for partner in self.env.ref('base.group_user').users.partner_id])
        except AccessError:
            pass
        return suggestions

    @api.model
    def get_mention_suggestions(self, search, limit=8, channel_id=None):
        """ Return 'limit'-first partners' id, name and email such that the name or email matches a
            'search' string. Prioritize users, and then extend the research to all partners.
            If channel_id is given, only members of this channel are returned.
        """
        search_dom = expression.OR([[('name', 'ilike', search)], [('email', 'ilike', search)]])
        search_dom = expression.AND([[('active', '=', True), ('type', '!=', 'private')], search_dom])
        if channel_id:
            search_dom = expression.AND([[('channel_ids', 'in', channel_id)], search_dom])

        # Search users
        domain = expression.AND([[('user_ids.id', '!=', False), ('user_ids.active', '=', True)], search_dom])
        users = self.search(domain, limit=limit)

        # Search partners if less than 'limit' users found
        partners = self.env['res.partner']
        if len(users) < limit:
            partners = self.search(expression.AND([[('id', 'not in', users.ids)], search_dom]), limit=limit)

        return [
            [partner.mail_partner_format() for partner in users],
            [partner.mail_partner_format() for partner in partners],
        ]

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
        if self.env['mail.channel'].check_access_rights('create', raise_exception=False):
            name = '%' + name + '%'
            excluded_partner_ids = [self.env.user.partner_id.id]
            self.env.cr.execute("""
                SELECT
                    U.id as user_id,
                    P.id as id,
                    P.name as name,
                    CASE WHEN B.last_poll IS NULL THEN 'offline'
                         WHEN age(now() AT TIME ZONE 'UTC', B.last_poll) > interval %s THEN 'offline'
                         WHEN age(now() AT TIME ZONE 'UTC', B.last_presence) > interval %s THEN 'away'
                         ELSE 'online'
                    END as im_status
                FROM res_users U
                    JOIN res_partner P ON P.id = U.partner_id
                    LEFT JOIN bus_presence B ON B.user_id = U.id
                WHERE P.name ILIKE %s
                    AND P.id NOT IN %s
                    AND U.active = 't'
                LIMIT %s
            """, ("%s seconds" % DISCONNECTION_TIMER, "%s seconds" % AWAY_TIMER, name, tuple(excluded_partner_ids), limit))
            return self.env.cr.dictfetchall()
        else:
            return {}
