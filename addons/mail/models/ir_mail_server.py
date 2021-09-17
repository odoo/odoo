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
        parameter if they are set. """
        bounce_email = self._alias_get_bounce_email()
        if bounce_email:
            return bounce_email
        return super()._get_default_from_address()

    @api.model
    def _get_default_from_address(self):
        """ Compute the default from address. If no complete default from is
        already defined, try to use mail-define config parameters. """
        email_from = self.env['ir.config_parameter'].sudo().get_param("mail.default.from")
        if email_from and "@" in email_from:
            return email_from
        catchall_domain = self._alias_get_catchall_domain()
        if email_from and catchall_domain:
            return f'{email_from}@{catchall_domain}'
        return super()._get_default_from_address()
