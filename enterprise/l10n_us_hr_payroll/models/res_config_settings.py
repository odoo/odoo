# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_us_ca_ett_tax = fields.Boolean(
        string="ETT Tax",
        related='company_id.l10n_us_ca_ett_tax',
        readonly=False)

    def action_open_suta_rule_parameters(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Configurate State Unemployment Taxes (SUI)"),
            "res_model": "hr.rule.parameter",
            "view_mode": "list,form",
            "domain": [('code', '=like', 'l10n_us_%_sui_%')],
        }
