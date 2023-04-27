# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    website_id = fields.Many2one('website', related='partner_id.website_id', store=True, related_sudo=False, readonly=False)

    _sql_constraints = [
        # Partial constraint, complemented by a python constraint (see below).
        ('login_key', 'unique (login, website_id)', 'You can not have two users with the same login!'),
    ]

    @api.constrains('login', 'website_id')
    def _check_login(self):
        """ Do not allow two users with the same login without website """
        self.flush(['login', 'website_id'])
        self.env.cr.execute(
            """SELECT login
                 FROM res_users
                WHERE login IN (SELECT login FROM res_users WHERE id IN %s AND website_id IS NULL)
                  AND website_id IS NULL
             GROUP BY login
               HAVING COUNT(*) > 1
            """,
            (tuple(self.ids),)
        )
        if self.env.cr.rowcount:
            raise ValidationError(_('You can not have two users with the same login!'))

    @api.model
    def _get_login_domain(self, login):
        website = self.env['website'].get_current_website()
        return super(ResUsers, self)._get_login_domain(login) + website.website_domain()

    @api.model
    def _get_login_order(self):
        return 'website_id, ' + super(ResUsers, self)._get_login_order()

    @api.model
    def _signup_create_user(self, values):
        current_website = self.env['website'].get_current_website()
        if request and current_website.specific_user_account:
            values['company_id'] = current_website.company_id.id
            values['company_ids'] = [(4, current_website.company_id.id)]
            values['website_id'] = current_website.id
        new_user = super(ResUsers, self)._signup_create_user(values)
        return new_user

    @api.model
    def _get_signup_invitation_scope(self):
        current_website = self.env['website'].get_current_website()
        return current_website.auth_signup_uninvited or super(ResUsers, self)._get_signup_invitation_scope()

    @classmethod
    def authenticate(cls, db, login, password, user_agent_env):
        """ Override to link the logged in user's res.partner to website.visitor.
        If both a request-based visitor and a user-based visitor exist we try
        to update them (have same partner_id), and move sub records to the main
        visitor (user one). Purpose is to try to keep a main visitor with as
        much sub-records (tracked pages, leads, ...) as possible. """
        uid = super(ResUsers, cls).authenticate(db, login, password, user_agent_env)
        if uid:
            with cls.pool.cursor() as cr:
                env = api.Environment(cr, uid, {})
                visitor_sudo = env['website.visitor']._get_visitor_from_request()
                if visitor_sudo:
                    user_partner = env.user.partner_id
                    other_user_visitor_sudo = env['website.visitor'].with_context(active_test=False).sudo().search(
                        [('partner_id', '=', user_partner.id), ('id', '!=', visitor_sudo.id)],
                        order='last_connection_datetime DESC',
                    )  # current 13.3 state: 1 result max as unique visitor / partner
                    if other_user_visitor_sudo:
                        visitor_main = other_user_visitor_sudo[0]
                        other_visitors = other_user_visitor_sudo[1:]  # normally void
                        (visitor_sudo + other_visitors)._link_to_visitor(visitor_main, keep_unique=True)
                        visitor_main.name = user_partner.name
                        visitor_main.active = True
                        visitor_main._update_visitor_last_visit()
                    else:
                        if visitor_sudo.partner_id != user_partner:
                            visitor_sudo._link_to_partner(
                                user_partner,
                                update_values={'partner_id': user_partner.id})
                        visitor_sudo._update_visitor_last_visit()
        return uid
