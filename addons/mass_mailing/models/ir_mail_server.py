# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.misc import format_date


class IrMail_Server(models.Model):
    _inherit = 'ir.mail_server'

    active_mailing_ids = fields.One2many(
        comodel_name='mailing.mailing',
        inverse_name='mail_server_id',
        string='Active mailing using this mail server',
        readonly=True,
        domain=[('state', '!=', 'done'), ('active', '=', True)])

    def _active_usages_compute(self):
        def format_usage(mailing_id):
            base = _('Mass Mailing "%s"', mailing_id.display_name)
            if not mailing_id.schedule_date:
                return base
            details = _('(scheduled for %s)', format_date(self.env, mailing_id.schedule_date))
            return f'{base} {details}'

        usages_super = super()._active_usages_compute()
        default_mail_server_id = self.env['mailing.mailing']._get_default_mail_server_id()
        for record in self:
            usages = []
            if default_mail_server_id == record.id:
                usages.append(_('Email Marketing uses it as its default mail server to send mass mailings'))
            usages.extend(map(format_usage, record.active_mailing_ids))
            if usages:
                usages_super.setdefault(record.id, []).extend(usages)
        return usages_super

    @api.constrains('owner_user_id')
    def _check_owner_user_id_not_mass_mailing(self):
        servers_with_owner = self.filtered('owner_user_id')
        if not servers_with_owner:
            return

        default_id = self.env['mailing.mailing']._get_default_mail_server_id()
        if default_id and default_id in servers_with_owner.ids:
            raise ValidationError(_(
                "Cannot set an owner on '%(server)s': it is configured as the dedicated Email Marketing server.",
                server=self.browse(default_id).display_name,
            ))

        used = self.env['mailing.mailing'].sudo().search([
            ('mail_server_id', 'in', servers_with_owner.ids),
            ('state', '!=', 'done'),
        ], limit=1)
        if used:
            raise ValidationError(_(
                "Cannot set an owner on '%(server)s': it is used by mailing '%(mailing)s'.",
                server=used.mail_server_id.display_name,
                mailing=used.display_name,
            ))
