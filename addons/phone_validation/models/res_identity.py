# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.phone_validation.tools import phone_validation


class ResIdentity(models.Model):
    _inherit = 'res.identity'

    phone_sanitized = fields.Char(
        string='Sanitized Phone', compute="_compute_phone_sanitized",
        compute_sudo=True, store=True)

    @api.depends('phone')
    def _compute_phone_sanitized(self):
        for identity in self:
            if not identity.phone:
                identity.phone_sanitized = False
                continue
            country_fname = False  # tde: fixme
            identity.phone_sanitized = phone_validation.phone_sanitize_numbers_w_record(
                [identity.phone],
                identity,
                record_country_fname=country_fname,
                force_format='E164'
            )[identity.phone]['sanitized']
