# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo import models, api, fields


class MrpBom(models.Model):
    _name = 'mrp.bom'
    _inherit = ['mrp.bom', 'analytic.mixin']

    # Company dependent JSON fields are not yet supported
    analytic_distribution_text = fields.Text(company_dependent=True)
    analytic_distribution = fields.Json(inverse="_inverse_analytic_distribution", store=False, precompute=False)
    analytic_account_ids = fields.Many2many('account.analytic.account', compute="_compute_analytic_account_ids", copy=True)

    @api.depends_context('company')
    @api.depends('analytic_distribution_text')
    def _compute_analytic_distribution(self):
        for record in self:
            record.analytic_distribution = json.loads(record.analytic_distribution_text or '{}')

    def _inverse_analytic_distribution(self):
        for record in self:
            record.analytic_distribution_text = json.dumps(record.analytic_distribution)

    @api.depends('analytic_distribution')
    def _compute_analytic_account_ids(self):
        for record in self:
            record.analytic_account_ids = bool(record.analytic_distribution) and self.env['account.analytic.account'].browse(
                list({int(account_id) for ids in record.analytic_distribution for account_id in ids.split(",")})
            ).exists()

    @api.onchange('product_id')
    def _onchange_analytic_distribution(self):
        for record in self:
            if record.product_id:
                record.analytic_distribution = record.env['account.analytic.distribution.model'].sudo()._get_distribution({
                    "product_id": record.product_id.id,
                    "product_categ_id": record.product_id.categ_id.id,
                    "company_id": record.company_id.id,
                })

    @api.constrains('analytic_distribution')
    def _check_analytic(self):
        for record in self:
            record.with_context({'validate_analytic': True})._validate_distribution(**{
                'product': record.product_id.id,
                'company_id': record.company_id.id,
            })
