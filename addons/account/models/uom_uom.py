# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class UoM(models.Model):
    _inherit = "uom.uom"

    fiscal_country_codes = fields.Char(compute="_compute_fiscal_country_codes")

    @api.depends_context("allowed_company_ids")
    def _compute_fiscal_country_codes(self):
        for record in self:
            record.fiscal_country_codes = ",".join(self.env.companies.mapped("account_fiscal_country_id.code"))
