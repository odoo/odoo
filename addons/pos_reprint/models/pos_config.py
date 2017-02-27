# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class PosConfig(models.Model):
    _inherit = 'pos.config'

    iface_reprint = fields.Boolean(
        string='Receipt Reprinting', help="This allows you to reprint a previously printed receipt.")

    @api.onchange('iface_reprint')
    def _onchange_iface_print(self):
        if self.iface_reprint:
            self.iface_print_via_proxy = self.iface_reprint

    @api.onchange('iface_print_via_proxy')
    def _onchange_iface_print_via_proxy(self):
        super(PosConfig, self)._onchange_iface_print_via_proxy()
        self.iface_reprint = self.iface_print_via_proxy if self.iface_reprint else None
