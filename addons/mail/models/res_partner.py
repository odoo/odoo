# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, fields, models, tools
from odoo.addons.bus.models.bus_presence import AWAY_TIMER
from odoo.addons.bus.models.bus_presence import DISCONNECTION_TIMER
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
        return {
            "id": self.name_get()[0][0],
            "display_name": self.name_get()[0][1],
            "name": self.name,
            "active": self.active,
            "im_status": self.im_status,
        }

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
        """ To be overwritten to return the id, name and email of partners used as static mention
            suggestions loaded once at webclient initialization and stored client side. """
        return []

    @api.model
    def get_mention_suggestions(self, search, limit=8):
        """ Return 'limit'-first partners' id, name and email such that the name or email matches a
            'search' string. Prioritize users, and then extend the research to all partners. """
        search_dom = expression.OR([[('name', 'ilike', search)], [('email', 'ilike', search)]])
        search_dom = expression.AND([[('active', '=', True)], search_dom])
        fields = ['id', 'name', 'email']

        # Search users
        domain = expression.AND([[('user_ids.id', '!=', False), ('user_ids.active', '=', True)], search_dom])
        users = self.search_read(domain, fields, limit=limit)

        # Search partners if less than 'limit' users found
        partners = []
        if len(users) < limit:
            partners = self.search_read(search_dom, fields, limit=limit)
            # Remove duplicates
            partners = [p for p in partners if not len([u for u in users if u['id'] == p['id']])] 

        # add OdooBot even if its partner is archived
        if len(partners) + len(users) < limit and "odoobot".startswith(search.lower()):
            odoobot = self.env.ref("base.partner_root")
            if not any(elem['id'] == odoobot.id for elem in partners):
                partners.append(odoobot.read(fields)[0])

        return [users, partners]

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
