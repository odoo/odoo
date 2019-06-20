# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Users(models.Model):
    _inherit = "res.users"

    def _get_default_unit(self):
        default_unit = self.env.user.l10n_in_unit_id
        allowed_units = self.env.company.l10n_in_unit_ids
        if default_unit not in allowed_units:
            return self.env.company.partner_id
        return self.env.user.l10n_in_unit_id

    l10n_in_unit_id = fields.Many2one(
        'res.partner',
        string="Current Unit",
        ondelete="restrict")

    @api.onchange('company_id')
    def _onchange_company(self):
        self.l10n_in_unit_id = self.company_id.partner_id
