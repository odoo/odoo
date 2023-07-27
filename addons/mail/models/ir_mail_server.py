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
        ICP = self.env['ir.config_parameter'].sudo()
        bounce_alias = ICP.get_param('mail.bounce.alias')
        domain = ICP.get_param('mail.catchall.domain')
        if bounce_alias and domain:
            return f'{bounce_alias}@{domain}'
        return super()._get_default_from_address()

    @api.model
    def _get_default_from_address(self):
        """ Compute the default from address. If no complete default from is
        already defined, try to use mail-define config parameters. """
        get_param = self.env['ir.config_parameter'].sudo().get_param
        email_from = get_param("mail.default.from")
        if email_from and "@" in email_from:
            return email_from
        domain = get_param("mail.catchall.domain")
        if email_from and domain:
            return f"{email_from}@{domain}"
        return super()._get_default_from_address()
