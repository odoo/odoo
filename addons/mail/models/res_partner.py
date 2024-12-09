# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

import odoo
from odoo import _, api, fields, models, tools
from odoo.osv import expression
from odoo.addons.mail.tools.discuss import Store

class Partner(models.Model):
    """ Update partner to add a field about notification preferences. Add a generic opt-out field that can be used
       to restrict usage of automatic email templates. """
    _name = "res.partner"
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
    def _get_view_cache_key(self, view_id=None, view_type='form', **options):
        """Add context variable force_email in the key as _get_view depends on it."""
        key = super()._get_view_cache_key(view_id, view_type, **options)
        return key + (self._context.get('force_email'),)

    @api.model
    @api.returns('self', lambda value: value.id)
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
    def _find_or_create_from_emails(self, emails, additional_values=None):
        """ Based on a list of emails, find or create partners. Additional values
        can be given to newly created partners. If an email is not unique (e.g.
        multi-email input), only the first found email is considered.

        Additional values allow to customize the created partner when context
        allows to give more information. It data is based on email normalized
        as it is the main information used in this method to distinguish or
        find partners.

        If no valid email is found for a given item, the given value is used to
        find partners with same invalid email or create a new one with the wrong
        value. It allows updating it afterwards. Notably with notifications
        resend it is possible to update emails, if only a typo prevents from
        having a real email for example.

        :param list emails: list of emails that may be formatted (each input
          will be parsed and normalized);
        :param dict additional_values: additional values per normalized email
          given to create if the partner is not found. Typically used to
          propagate a company_id and customer information from related record.
          Values for key 'False' are used when creating partner for invalid
          emails;

        :return: res.partner records in a list, following order of emails. It
          is not a recordset, to keep Falsy values.
        """
        additional_values = additional_values if additional_values else {}
        partners, tocreate_vals_list = self.env['res.partner'], []
        name_emails = [tools.parse_contact_from_email(email) for email in emails]

        # find valid emails_normalized, filtering out false / void values, and search
        # for existing partners based on those emails
        emails_normalized = {email_normalized
                             for _name, email_normalized in name_emails
                             if email_normalized}
        # find partners for invalid (but not void) emails, aka either invalid email
        # either no email and a name that will be used as email
        names = {
            name.strip()
            for name, email_normalized in name_emails
            if not email_normalized and name.strip()
        }
        if emails_normalized or names:
            domains = []
            if emails_normalized:
                domains.append([('email_normalized', 'in', list(emails_normalized))])
            if names:
                domains.append([('email', 'in', list(names))])
            partners += self.search(expression.OR(domains))

        # create partners for valid email without any existing partner. Keep
        # only first found occurrence of each normalized email, aka: ('Norbert',
        # 'norbert@gmail.com'), ('Norbert With Surname', 'norbert@gmail.com')'
        # -> a single partner is created for email 'norbert@gmail.com'
        seen = set()
        notfound_emails = (emails_normalized - set(partners.mapped('email_normalized'))) if partners else emails_normalized
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
        ]

        # create partners for invalid emails (aka name and not email_normalized)
        # without any existing partner
        tocreate_vals_list += [
            {
                self._rec_name: name,
                'email': name,
                **additional_values.get(False, {}),
            }
            for name in names if name not in partners.mapped('email')
        ]

        # create partners once
        if tocreate_vals_list:
            partners += self.create(tocreate_vals_list)

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

    def _to_store(self, store: Store, /, *, fields=None, main_user_by_partner=None):
        if fields is None:
            fields = ["active", "email", "im_status", "is_company", "name", "user", "write_date"]
        if not self.env.user._is_internal() and "email" in fields:
            fields.remove("email")
        for partner in self:
            data = partner._read_format(
                [
                    field
                    for field in fields
                    if field
                    not in ["country", "display_name", "isAdmin", "notification_type", "signature", "user"]
                ],
                load=False,
            )[0]
            if "country" in fields:
                c = partner.country_id
                data["country"] = {"code": c.code, "id": c.id, "name": c.name} if c else False
            if "display_name" in fields:
                data["displayName"] = partner.display_name
            if 'user' in fields:
                main_user = main_user_by_partner and main_user_by_partner.get(partner)
                if not main_user:
                    users = partner.with_context(active_test=False).user_ids
                    internal_users = users - users.filtered("share")
                    main_user = (
                        internal_users[0]
                        if len(internal_users) > 0
                        else users[0] if len(users) > 0 else self.env["res.users"]
                    )
                data['userId'] = main_user.id
                data["isInternalUser"] = not main_user.share if main_user else False
                if "isAdmin" in fields:
                    data["isAdmin"] = main_user._is_admin()
                if "notification_type" in fields:
                    data["notification_preference"] = main_user.notification_type
                if "signature" in fields:
                    data["signature"] = main_user.signature
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
    def _search_mention_suggestions(self, domain, limit):
        domain_is_user = expression.AND([[('user_ids', '!=', False)], [('user_ids.active', '=', True)], domain])
        priority_conditions = [
            expression.AND([domain_is_user, [('partner_share', '=', False)]]),  # Search partners that are internal users
            domain_is_user,  # Search partners that are users
            domain,  # Search partners that are not users
        ]
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

    @api.readonly
    @api.model
    def im_search(self, name, limit=20, excluded_ids=None):
        """ Search partner with a name and return its id, name and im_status.
            Note : the user must be logged
            :param name : the partner name to search
            :param limit : the limit of result to return
            :param excluded_ids : the ids of excluded partners
        """
        # This method is supposed to be used only in the context of channel creation or
        # extension via an invite. As both of these actions require the 'create' access
        # right, we check this specific ACL.
        if excluded_ids is None:
            excluded_ids = []
        users = self.env['res.users'].search([
            ('id', '!=', self.env.user.id),
            ('name', 'ilike', name),
            ('active', '=', True),
            ('share', '=', False),
            ('partner_id', 'not in', excluded_ids)
        ], order='name, id', limit=limit)
        return Store(users.partner_id).get_result()

    @api.model
    def _get_current_persona(self):
        if not self.env.user or self.env.user._is_public():
            return (self.env["res.partner"], self.env["mail.guest"]._get_guest_from_context())
        return (self.env.user.partner_id, self.env["mail.guest"])
