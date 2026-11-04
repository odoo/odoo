# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class IrMailServer(models.Model):
    _name = 'ir.mail_server'
    _inherit = ['ir.mail_server']

    mail_template_ids = fields.One2many(
        comodel_name='mail.template',
        inverse_name='mail_server_id',
        string='Mail template using this mail server',
        readonly=True)

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
