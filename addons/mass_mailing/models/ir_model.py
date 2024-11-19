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
        if operator not in ('in', 'not in'):
            return NotImplemented

        valid_models = self.search([]).filtered(
            lambda model: model.model in self.env
            and not model.is_transient()
            and getattr(self.env[model.model], '_mailing_enabled', False)
        )

        return [('id', operator, valid_models.ids)]
