# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


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
