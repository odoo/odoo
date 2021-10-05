# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    account_analytic_id = fields.Many2one(compute='_compute_analytic_id', store=True, readonly=False)
    analytic_tag_ids = fields.Many2many(compute='_compute_tag_ids', store=True, readonly=False)

    @api.depends('product_id', 'date_order')
    def _compute_analytic_id(self):
        for rec in self:
            if not rec.account_analytic_id:
                default_analytic_account = rec.env['account.analytic.default'].sudo().account_get(
                    product_id=rec.product_id.id,
                    partner_id=rec.order_id.partner_id.id,
                    user_id=rec.env.uid,
                    date=rec.date_order,
                    company_id=rec.company_id.id,
                )
                rec.account_analytic_id = default_analytic_account.analytic_id

    @api.depends('product_id', 'date_order')
    def _compute_tag_ids(self):
        for rec in self:
            if not rec.analytic_tag_ids:
                default_analytic_account = rec.env['account.analytic.default'].sudo().account_get(
                    product_id=rec.product_id.id,
                    partner_id=rec.order_id.partner_id.id,
                    user_id=rec.env.uid,
                    date=rec.date_order,
                    company_id=rec.company_id.id,
                )
                rec.analytic_tag_ids = default_analytic_account.analytic_tag_ids
