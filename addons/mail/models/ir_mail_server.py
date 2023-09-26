# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


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
                map(lambda t: _('%s (Email Template)', t.display_name), record.mail_template_ids)
            )
        return usages_super

    @api.model
    def _get_default_bounce_address(self):
        """ Compute the default bounce address. Try to use mail-defined config
        parameter bounce alias if set. """
        ICP = self.env['ir.config_parameter'].sudo()
        bounce_alias = ICP.get_param('mail.bounce.alias')
        domain = ICP.get_param('mail.catchall.domain')
        if bounce_alias and domain:
            return f'{bounce_alias}@{domain}'
        return super()._get_default_bounce_address()

    @api.model
    def _get_default_from_address(self):
        """ Default from: try to use ``mail.default.from`` ICP either as a
        full email address, either completed with ``mail.catchall.domain``
        to form a alias-based default from. """
        get_param = self.env['ir.config_parameter'].sudo().get_param
        email_from = get_param("mail.default.from")
        if email_from and "@" in email_from:
            return email_from
        if email_from:
            if domain := get_param("mail.catchall.domain"):
                return f"{email_from}@{domain}"
        return super()._get_default_from_address()

    def _get_test_email_from(self):
        self.ensure_one()
        if from_filter_parts := [part.strip() for part in (self.from_filter or '').split(",") if part.strip()]:
            # find first found complete email in filter parts
            if mail_from := next((email for email in from_filter_parts if "@" in email), None):
                return mail_from
            # try to complete with default.from in same domain of first found filter parts
            default_from = self.env["ir.config_parameter"].sudo().get_param("mail.default.from", "odoo")
            if "@" not in default_from:
                return f"{default_from}@{from_filter_parts[0]}"
            # the mail server is configured for a domain that matches the default email address
            if self._match_from_filter(default_from, self.from_filter):
                return default_from
        # no from_filter or from_filter is configured for a domain different that
        # the one of the full email configured in mail.default.from -> fallback
        return super()._get_test_email_from()
