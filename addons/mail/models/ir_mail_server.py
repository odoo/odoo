# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import email_normalize


class IrMail_Server(models.Model):
    _inherit = 'ir.mail_server'
    _email_field = 'smtp_user'

    mail_template_ids = fields.One2many(
        comodel_name='mail.template',
        inverse_name='mail_server_id',
        string='Mail template using this mail server',
        readonly=True)

    owner_user_id = fields.Many2one('res.users', 'Owner')

    # Store the current time, and the number of emails we sent
    # Each minute, the time and the count will be reset
    # Used to throttle the number of emails we send for the personal
    # mail servers.
    owner_limit_time = fields.Datetime('Owner Limit Time')
    owner_limit_count = fields.Integer('Owner Limit Count')

    _unique_owner_user_id = models.Constraint(
        "UNIQUE(owner_user_id)",
        "owner_user_id must be unique",
    )

    def _active_usages_compute(self):
        usages_super = super()._active_usages_compute()
        for record in self.filtered('mail_template_ids'):
            usages_super.setdefault(record.id, []).extend(
                self.env._('%s (Email Template)', t.display_name)
                for t in record.mail_template_ids
            )
        return usages_super

    @api.model
    def _get_default_bounce_address(self):
        """ Compute the default bounce address. Try to use mail-defined config
        parameter bounce alias if set. """
        if self.env.company.bounce_email:
            return self.env.company.bounce_email
        return super()._get_default_bounce_address()

    @api.model
    def _get_default_from_address(self):
        """ Default from: try to use default_from defined on company's alias
        domain. """
        if default_from := self.env.company.default_from_email:
            return default_from
        return super()._get_default_from_address()

    def _get_test_email_from(self):
        self.ensure_one()
        if from_filter_parts := [part.strip() for part in (self.from_filter or '').split(",") if part.strip()]:
            # find first found complete email in filter parts
            if mail_from := next((email for email in from_filter_parts if "@" in email), None):
                return mail_from
            # the mail server is configured for a domain that matches the default email address
            alias_domains = self.env['mail.alias.domain'].sudo().search([])
            matching = next(
                (alias_domain for alias_domain in alias_domains
                 if self._match_from_filter(alias_domain.default_from_email, self.from_filter)
                ), False
            )
            if matching:
                return matching.default_from_email
            # fake default_from "odoo@domain"
            return f"odoo@{from_filter_parts[0]}"
        # no from_filter or from_filter is configured for a domain different that
        # the default_from of company's alias_domain -> fallback
        return super()._get_test_email_from()

    @api.model
    def _filter_mail_servers_fallback(self, servers):
        return servers.filtered(lambda s: not s.owner_user_id)

    def _find_mail_server_allowed_domain(self):
        """Restrict search to 'public' servers."""
        domain = super()._find_mail_server_allowed_domain()
        domain &= Domain('owner_user_id', '=', False)
        return domain

    def _check_forced_mail_server(self, mail_server, allow_archived, smtp_from):
        super()._check_forced_mail_server(mail_server, allow_archived, smtp_from)

        if mail_server.owner_user_id:
            if email_normalize(smtp_from) != mail_server.from_filter:
                raise UserError(_('The server "%s" cannot be forced as it belongs to a user.', mail_server.display_name))
            if not mail_server.active:
                raise UserError(_('The server "%s" cannot be forced as it belongs to a user and is archived.', mail_server.display_name))
            if mail_server.owner_user_id.outgoing_mail_server_id != mail_server:
                raise UserError(_('The server "%s" cannot be forced as the owner does not use it anymore.', mail_server.display_name))

    def _get_personal_mail_servers_limit(self):
        """Return the number of email we can send in 1 minutes for this outgoing server.

        0 fallbacks to 30 to avoid blocking servers.
        """
        return int(self.env['ir.config_parameter'].sudo().get_param('mail.server.personal.limit.minutes')) or 30
