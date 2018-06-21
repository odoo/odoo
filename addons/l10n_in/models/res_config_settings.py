# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    show_module_l10n_in = fields.Boolean(compute='_compute_show_module_l10n_in')
    group_l10n_in_reseller = fields.Boolean(implied_group='l10n_in.group_l10n_in_reseller', string="Manage Reseller(E-Commerce)")

    @api.depends('company_id')
    def _compute_show_module_l10n_in(self):
        self.show_module_l10n_in = self.company_id.country_id.code == 'IN'
