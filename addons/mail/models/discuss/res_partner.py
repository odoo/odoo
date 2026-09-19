# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import email_normalize
from odoo.tools.mail import email_re
from odoo.addons.mail.tools.discuss import Store
from odoo.exceptions import AccessError


class ResPartner(models.Model):
    _inherit = "res.partner"

    channel_ids = fields.Many2many(
        "discuss.channel",
        "discuss_channel_member",
        "partner_id",
        "channel_id",
        string="Channels",
        copy=False,
    )
    channel_member_ids = fields.One2many("discuss.channel.member", "partner_id")
    is_in_call = fields.Boolean(compute="_compute_is_in_call", groups="base.group_system")
    rtc_session_ids = fields.One2many("discuss.channel.rtc.session", "partner_id")

    @api.depends("rtc_session_ids")
    def _compute_is_in_call(self):
        for partner in self:
            partner.is_in_call = bool(partner.rtc_session_ids)

    @api.depends("name", "email")
    @api.depends_context("display_email", "formatted_display_name")
    def _compute_display_name(self):
        if not self.env.context.get("display_email"):
            super()._compute_display_name()
            return
        for partner in self:
            if self.env.context.get("formatted_display_name"):
                partner.display_name = f"{partner.name}" + (f" --({partner.email})--" if partner.email else "")
            else:
                partner.display_name = f"{partner.name}" + (f" ({partner.email})" if partner.email else "")

    @api.readonly
    @api.model
    def search_for_channel_invite(
        self,
        search_term,
        exact_match_terms=None,
        channel_id=None,
        limit=30,
        with_portal_users=False,
    ):
        """Returns partners matching search_term that can be invited to a channel.

        This method supports multiple search terms separated by commas,
        Any of those terms can match the name or email of a partner.

        If invite by email is allowed, it also returns a list of emails
        that can be invited to the channel.
        This list will not include emails that are already known to the channel
        (i.e. already a member or already invited).

        :param exact_match_terms: subset of ``search_term`` (e.g. pasted from a spreadsheet)
            that must match a partner's name or email exactly, instead of the fuzzy
            ``ilike`` match used for the rest of ``search_term``. Each can match at most one
            partner, so they are not subject to ``limit``, and are returned separately as
            ``exact_match_partner_ids`` for the frontend to select directly.
        :param with_portal_users: whether portal users may be included in the results. Should
            only be set when the channel configuration actually allows portal users to be
            invited (e.g. a "group" channel), as including them is significantly more expensive.
        """
        store = Store()
        exact_match_terms = exact_match_terms or []
        channel = self.env["discuss.channel"].search_fetch([("id", "=", channel_id)])
        partners, exact_match_partners = self._search_for_multiple_channel_invites(
            store, search_term, exact_match_terms, channel, limit, with_portal_users
        )
        selectable_emails = []
        emails_already_sent = []
        if channel._allow_invite_by_email():
            emails_normalized = [email_normalize(e) for e in email_re.findall(search_term) if e]
            if emails_normalized:
                member_domain = Domain(
                    [("channel_id", "=", channel.id), ("invitation_sent_dt", "=", False)]
                )
                member_domain &= (
                    Domain("guest_id.email_normalized", "in", emails_normalized)
                    | Domain("partner_id.email_normalized", "in", emails_normalized)
                )
                email_members = self.env["discuss.channel.member"].search_fetch(member_domain)
                known_emails = set(
                    email_members.mapped(
                        lambda m: m.partner_id.email_normalized or m.guest_id.email_normalized
                    )
                ) | set((partners | exact_match_partners).mapped("email_normalized"))
                # This keeps the order of the emails as they were in the search term,
                # while removing duplicates and known emails.
                seen = set()
                for email in emails_normalized:
                    if email not in known_emails and email not in seen:
                        seen.add(email)
                        selectable_emails.append(email)

                # sudo - mail.mail: checking mail records to determine if an email was already sent is acceptable.
                emails_already_sent = {email for (email,) in self.env["mail.mail"]
                    .sudo()
                    ._read_group(
                        [
                            ("email_to", "in", selectable_emails),
                            ("model", "=", "discuss.channel"),
                            ("res_id", "=", channel.id),
                        ],
                        ["email_to"],
                    )}
        return {
            "emails_already_sent": list(emails_already_sent),
            "exact_match_partner_ids": exact_match_partners.ids,
            "partner_ids": partners.ids,
            "selectable_emails": selectable_emails,
            "store_data": store,
        }

    @api.model
    def _get_channel_invite_domain(self, channel, with_portal_users=False):
        """Returns the domain of the partners that may be invited to ``channel``.

        Shared by the Discuss invitation panel and the back-end channel form, so
        that both propose the same candidates.

        :param channel: channel to invite to, empty recordset to only apply the
            channel independent conditions.
        :type channel: discuss.channel
        :param with_portal_users: whether portal users may be included in the results.
        """
        domain = Domain.AND(
            [
                [("active", "=", True)],
                [("user_ids", "!=", False)],
                [("user_ids.active", "=", True)],
            ],
        )
        if not with_portal_users:
            domain &= Domain("user_ids.share", "=", False)
        if channel:
            domain &= Domain("channel_ids", "not in", channel.id)
            if channel.group_public_id:
                domain &= Domain("user_ids.all_group_ids", "in", channel.group_public_id.id)
        return domain

    @api.readonly
    @api.model
    def _search_for_multiple_channel_invites(
        self,
        store: Store,
        search_term,
        exact_match_terms,
        channels,
        limit=30,
        with_portal_users=False,
    ):
        """Returns partners matching search_term that can be invited to any of the given channels.

        This method supports multiple search terms separated by commas,
        Any of those terms can match the name or email of a partner. Only the first ``limit``
        are used.

        :param exact_match_terms: subset of terms that must match a partner's name or email
            exactly; they are excluded from the fuzzy ``ilike`` search on the other terms, and
            not subject to ``limit`` (see :meth:`search_for_channel_invite`).
        """
        search_term_splitted = [stripped for s in search_term.split(",") if (stripped := s.strip())]
        search_term_splitted = [
            term for term in search_term_splitted if term not in exact_match_terms
        ]
        return self._search_for_channel_invite(
            store,
            search_term_splitted[:limit],
            exact_match_terms,
            channels,
            limit,
            with_portal_users,
        )

    @api.readonly
    @api.model
    def _search_for_channel_invite(
        self,
        store: Store,
        search_term,
        exact_match_terms=None,
        channel=None,
        limit=30,
        with_portal_users=False,
    ):
        if channel is None:
            channel = self.env["discuss.channel"]
        if isinstance(search_term, list):
            search_term_list = search_term
        else:
            search_term_list = [search_term]
        exact_match_terms = exact_match_terms or []
        base_domain = self._get_channel_invite_domain(channel, with_portal_users) & Domain(
            "id", "!=", self.env.user.partner_id.id
        )
        selectable_partners = self.env["res.partner"]
        if search_term_list:
            fuzzy_domain = base_domain & Domain.OR(
                [
                    Domain("name", "ilike", term) | Domain("email", "ilike", term)
                    for term in search_term_list
                ]
            )
            selectable_partners = self.search(fuzzy_domain, limit=limit + 1, order="name, id")
        exact_match_partners = self.env["res.partner"]
        if exact_match_terms:
            exact_domains = [Domain("name", "=", term) for term in exact_match_terms]
            exact_domains += [
                Domain("email_normalized", "=", normalized_email)
                for term in exact_match_terms
                if (normalized_email := email_normalize(term))
            ]
            exact_match_partners = self.search(
                base_domain & Domain.OR(exact_domains), order="name, id"
            )
        store.add(
            selectable_partners | exact_match_partners,
            "_store_channel_invite_fields",
            fields_params={"channel": channel},
        )
        return selectable_partners, exact_match_partners

    def _store_channel_invite_fields(self, res: Store.FieldList, *, channel):
        self._store_partner_fields(res)

    @api.readonly
    @api.model
    def get_mention_suggestions_from_channel(self, channel_id, search, limit=8):
        """Return 'limit'-first partners' such that the name or email matches a 'search' string.
        Prioritize partners that are also (internal) users, and then extend the research to all partners.
        Only members of the given channel are returned.
        """
        channel = self.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            return []
        domain = Domain([
            self._get_mention_suggestions_domain(search),
            ("channel_ids", "in", (channel.parent_channel_id | channel).ids)
        ])
        extra_domain = Domain([
            ('user_ids', '!=', False),
            ('user_ids.active', '=', True),
            ('partner_share', '=', False),
        ])
        allowed_group = (channel.parent_channel_id or channel).group_public_id
        if allowed_group:
            extra_domain &= Domain("user_ids.all_group_ids", "in", allowed_group.id)
        partners = self._search_mention_suggestions(domain, limit, extra_domain)
        members_domain = [
            ("channel_id", "in", (channel.parent_channel_id | channel).ids),
            ("partner_id", "in", partners.ids)
        ]
        members = self.env["discuss.channel.member"].search(members_domain)
        store = Store()
        store.add(members, "_store_identifying_fields")
        store.add(
            partners,
            lambda res: (
                res.from_method("_store_partner_fields"),
                res.from_method("_store_mention_fields"),
            ),
        )
        store.add(channel, ["group_public_id"])
        if allowed_group:
            for p in partners:
                store.add(p, {"group_ids": [("ADD", (allowed_group & p.user_ids.all_group_ids).ids)]})
        try:
            roles = self.env["res.role"].search([("name", "ilike", search)], limit=8)
            store.add(roles, ["name", "user_ids_count"])
        except AccessError:
            pass
        return store
