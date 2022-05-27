# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Company(models.Model):
    _inherit = 'res.company'

    hr_presence_control_email_amount = fields.Integer(string="# emails to send")
    hr_presence_control_ip_list = fields.Char(string="Valid IP addresses")

    def _install_hr_localizations(self):
        if any(c.partner_id.country_id.code == 'MX' for c in self):
            l10n_mx = self.env['ir.module.module'].sudo().search([
                ('name', '=', 'l10n_mx_hr'),
                ('state', 'not in', ['installed', 'to install', 'to upgrade']),
            ])
            if l10n_mx:
                l10n_mx.button_immediate_install()

    def create(self, vals_list):
        res = super().create(vals_list)
        res._install_hr_localizations()
        return res

    def write(self, vals):
        res = super().write(vals)
        if 'country_id' in vals:
            self._install_hr_localizations()
        return res
