# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

import odoo
from odoo import _, api, fields, models, tools
from odoo.osv import expression
from odoo.addons.mail.tools.discuss import Store


class ResPartner(models.Model):
    """ Update partner to add a field about notification preferences. Add a generic opt-out field that can be used
       to restrict usage of automatic email templates. """
    _name = 'res.partner'
    _inherit = ['res.partner', 'mail.activity.mixin', 'mail.thread.blacklist']
    _mail_flat_thread = False

    # override to add and order tracking
    name = fields.Char(tracking=1)
    email = fields.Char(tracking=1)
    phone = fields.Char(tracking=2)
    parent_id = fields.Many2one(tracking=3)
    user_id = fields.Many2one(tracking=4)
    vat = fields.Char(tracking=5)
    # tracked field used for chatter logging purposes
    # we need this to be readable inline as tracking messages use inline HTML nodes
    contact_address_inline = fields.Char(compute='_compute_contact_address_inline', string='Inlined Complete Address', tracking=True)
    starred_message_ids = fields.Many2many('mail.message', 'mail_message_res_partner_starred_rel')

    @api.depends('contact_address')
    def _compute_contact_address_inline(self):
        """Compute an inline-friendly address based on contact_address."""
        for partner in self:
            # replace any successive \n with a single comma
            partner.contact_address_inline = re.sub(r'\n(\s|\n)*', ', ', partner.contact_address).strip().strip(',')

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

    # ------------------------------------------------------------
    # MESSAGING
    # ------------------------------------------------------------

    def _mail_get_partners(self, introspect_fields=False):
        return dict((partner.id, partner) for partner in self)

    def _message_get_suggested_recipients(self):
        recipients = super()._message_get_suggested_recipients()
        self._message_add_suggested_recipient(recipients, partner=self, reason=_('Partner Profile'))
        return recipients

    def _message_get_default_recipients(self):
        return {
            r.id:
            {
                'partner_ids': [r.id],
                'email_to': False,
                'email_cc': False,
            }
            for r in self
        }

    # ------------------------------------------------------------
    # ORM
    # ------------------------------------------------------------
    @api.model
    def _get_view_cache_key(self, view_id=None, view_type='form', **options):
        """Add context variable force_email in the key as _get_view depends on it."""
        key = super()._get_view_cache_key(view_id, view_type, **options)
        return key + (self._context.get('force_email'),)

    @api.model
    def find_or_create(self, email, assert_valid_email=False):
        """ Override to use the email_normalized field. """
        if not email:
            raise ValueError(_('An email is required for find_or_create to work'))

        parsed_name, parsed_email_normalized = tools.parse_contact_from_email(email)
        if not parsed_email_normalized and assert_valid_email:
            raise ValueError(_('%(email)s is not recognized as a valid email. This is required to create a new customer.'))
        if parsed_email_normalized:
            partners = self.search([('email_normalized', '=', parsed_email_normalized)], limit=1)
            if partners:
                return partners

        # We don't want to call `super()` to avoid searching twice on the email
        # Especially when the search `email =ilike` cannot be as efficient as
        # a search on email_normalized with a btree index
        # If you want to override `find_or_create()` your module should depend on `mail`
        create_values = {self._rec_name: parsed_name or parsed_email_normalized}
        if parsed_email_normalized:  # otherwise keep default_email in context
            create_values['email'] = parsed_email_normalized
        return self.create(create_values)

    @api.model
    def _find_or_create_from_emails(self, emails, ban_emails=None,
                                    filter_found=None, additional_values=None,
                                    no_create=False, sort_key=None, sort_reverse=True):
        """ Based on a list of emails, find or (optionally) create partners.
        If an email is not unique (e.g. multi-email input), only the first found
        valid email in input is considered. Filter and sort options allow to
        tweak the way we link emails to partners (e.g. share partners only, ...).

        Optional additional values allow to customize the created partner. Data
        are given per normalized email as it the creation criterion.

        When an email is invalid but not void, it is used for search or create.
        It allows updating it afterwards e.g. with notifications resend which
        allows fixing typos / wrong emails.

        :param list emails: list of emails that can be formatted;
        :param list ban_emails: optional list of banished emails e.g. because
          it may interfere with master data like aliases;
        :param callable filter_found: if given, filters found partners based on emails;
        :param dict additional_values: additional values per normalized or
          raw invalid email given to partner creation. Typically used to
          propagate a company_id and customer information from related record.
          If email cannot be normalized, raw value is used as dict key instead;
        :param sort_key: an optional sorting key for sorting partners before
          finding one with matching email normalized. When several partners
          have the same email, users might want to give a preference based
          on e.g. company, being a customer or not, ... Default ordering is
          to use 'id ASC', which means older partners first as they are considered
          as more relevant compared to default 'complete_name';
        :param bool sort_reverse: given to sorted (see 'reverse' argument of sort);
        :param bool no_create: skip the 'create' part of 'find or create'. Allows
          to use tool as 'find and sort' without adding new partners in db;

        :return: res.partner records in a list, following order of emails. Using
          a list allows to to keep Falsy values when no match;
        :rtype: list
        """
        additional_values = additional_values or {}
        partners, tocreate_vals_list = self.env['res.partner'], []
        name_emails = [tools.parse_contact_from_email(email) for email in emails]

        # find valid emails_normalized, filtering out false / void values, and search
        # for existing partners based on those emails
        emails_normalized = {email_normalized
                             for _name, email_normalized in name_emails
                             if email_normalized and email_normalized not in (ban_emails or [])}
        # find partners for invalid (but not void) emails, aka either invalid email
        # either no email and a name that will be used as email
        names = {
            name.strip()
            for name, email_normalized in name_emails
            if not email_normalized and name.strip() and name.strip() not in (ban_emails or [])
        }
        if emails_normalized or names:
            domains = []
            if emails_normalized:
                domains.append([('email_normalized', 'in', list(emails_normalized))])
            if names:
                domains.append([('email', 'in', list(names))])
            partners += self.search(expression.OR(domains), order='id ASC')
            if filter_found:
                partners = partners.filtered(filter_found)

        if not no_create:
            # create partners for valid email without any existing partner. Keep
            # only first found occurrence of each normalized email, aka: ('Norbert',
            # 'norbert@gmail.com'), ('Norbert With Surname', 'norbert@gmail.com')'
            # -> a single partner is created for email 'norbert@gmail.com'
            seen = set()
            notfound_emails = emails_normalized - set(partners.mapped('email_normalized'))
            notfound_name_emails = [
                name_email
                for name_email in name_emails
                if name_email[1] in notfound_emails and name_email[1] not in seen
                and not seen.add(name_email[1])
            ]
            tocreate_vals_list += [
                {
                    self._rec_name: name or email_normalized,
                    'email': email_normalized,
                    **additional_values.get(email_normalized, {}),
                }
                for name, email_normalized in notfound_name_emails
                if email_normalized not in (ban_emails or [])
            ]
            # create partners for invalid emails (aka name and not email_normalized)
            # without any existing partner
            tocreate_vals_list += [
                {
                    self._rec_name: name,
                    'email': name,
                    **additional_values.get(name, {}),
                }
                for name in names if name not in partners.mapped('email') and name not in (ban_emails or [])
            ]
            # create partners once
            if tocreate_vals_list:
                partners += self.create(tocreate_vals_list)

        # sort partners (already ordered based on search)
        if sort_key:
            partners = partners.sorted(key=sort_key, reverse=sort_reverse)

        return [
            next(
                (partner for partner in partners
                    if (email_normalized and partner.email_normalized == email_normalized)
                    or (not email_normalized and email and partner.email == email)
                    or (not email_normalized and name and partner.name == name)
                ),
                self.env['res.partner']
            )
            for (name, email_normalized), email in zip(name_emails, emails)
        ]

    # ------------------------------------------------------------
    # DISCUSS
    # ------------------------------------------------------------

    def _to_store_defaults(self):
        return ["active", "email", "im_status", "is_company", "name", "user", "write_date"]

    def _to_store(self, store: Store, fields, *, main_user_by_partner=None):
        if not self.env.user._is_internal() and "email" in fields:
            fields.remove("email")
        store.add_records_fields(
            self,
            [
                field
                for field in fields
                if field not in ["display_name", "isAdmin", "notification_type", "signature", "user"]
            ],
        )
        for partner in self:
            data = {}
            if "display_name" in fields:
                data["displayName"] = partner.display_name
            if "user" in fields:
                main_user = main_user_by_partner and main_user_by_partner.get(partner)
                if not main_user:
                    users = partner.with_context(active_test=False).user_ids
                    internal_users = users - users.filtered("share")
                    main_user = internal_users[:1] or users[:1]
                data["userId"] = main_user.id
                data["isInternalUser"] = not main_user.share if main_user else False
                if "isAdmin" in fields:
                    data["isAdmin"] = main_user._is_admin()
                if "notification_type" in fields:
                    data["notification_preference"] = main_user.notification_type
                if "signature" in fields:
                    data["signature"] = main_user.signature
            if data:
                store.add(partner, data)

    @api.readonly
    @api.model
    def get_mention_suggestions(self, search, limit=8):
        """ Return 'limit'-first partners' such that the name or email matches a 'search' string.
            Prioritize partners that are also (internal) users, and then extend the research to all partners.
            The return format is a list of partner data (as per returned by `_to_store()`).
        """
        domain = self._get_mention_suggestions_domain(search)
        partners = self._search_mention_suggestions(domain, limit)
        return Store(partners).get_result()

    @api.model
    def _get_mention_suggestions_domain(self, search):
        return expression.AND([
            expression.OR([
                [('name', 'ilike', search)],
                [('email', 'ilike', search)],
            ]),
            [('active', '=', True)],
        ])

    @api.model
    def _search_mention_suggestions(self, domain, limit, extra_domain=None):
        domain_is_user = expression.AND([[('user_ids', '!=', False)], [('user_ids.active', '=', True)], domain])
        priority_conditions = [
            expression.AND([domain_is_user, [('partner_share', '=', False)]]),  # Search partners that are internal users
            domain_is_user,  # Search partners that are users
            domain,  # Search partners that are not users
        ]
        if extra_domain:
            priority_conditions.append(extra_domain)
        partners = self.env['res.partner']
        for domain in priority_conditions:
            remaining_limit = limit - len(partners)
            if remaining_limit <= 0:
                break
            # We are using _search to avoid the default order that is
            # automatically added by the search method. "Order by" makes the query
            # really slow.
            query = self._search(expression.AND([[('id', 'not in', partners.ids)], domain]), limit=remaining_limit)
            partners |= self.browse(query)
        return partners

    @api.model
    def _get_current_persona(self):
        if not self.env.user or self.env.user._is_public():
            return (self.env["res.partner"], self.env["mail.guest"]._get_guest_from_context())
        return (self.env.user.partner_id, self.env["mail.guest"])

    def _can_return_content(self, field_name=None, access_token=None):
        # access to the avatar is allowed if there is access to the messages
        if field_name == "avatar_128" and self.env["mail.message"].search_count(
            [("author_id", "=", self.id)], limit=1
        ):
            return True
        return super()._can_return_content(field_name, access_token)
