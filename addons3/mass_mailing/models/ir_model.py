# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class IrModel(models.Model):
    _inherit = 'ir.model'

    is_mailing_enabled = fields.Boolean(
        string="Mailing Enabled",
        compute='_compute_is_mailing_enabled', search='_search_is_mailing_enabled',
        help="Whether this model supports marketing mailing capabilities (notably email and SMS).",
    )

    def _compute_is_mailing_enabled(self):
        for model in self:
            model.is_mailing_enabled = getattr(self.env[model.model], '_mailing_enabled', False)

    def _search_is_mailing_enabled(self, operator, value):
        if operator not in ('=', '!='):
            raise ValueError(_("Searching Mailing Enabled models supports only direct search using '='' or '!='."))

        valid_models = self.env['ir.model']
        for model in self.search([]):
            if model.model not in self.env or model.is_transient():
                continue
            if getattr(self.env[model.model], '_mailing_enabled', False):
                valid_models |= model

        search_is_mailing_enabled = (operator == '=' and value) or (operator == '!=' and not value)
        if search_is_mailing_enabled:
            return [('id', 'in', valid_models.ids)]
        return [('id', 'not in', valid_models.ids)]
