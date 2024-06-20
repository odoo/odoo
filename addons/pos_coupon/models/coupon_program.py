# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# NOTE Use black to automatically format this code.

from odoo import api, fields, models, _

import ast

class CouponProgram(models.Model):
    _inherit = "coupon.program"

    pos_config_ids = fields.Many2many(
        "pos.config",
        string="Point of Sales",
        readonly=True,
    )
    pos_order_line_ids = fields.One2many(
        "pos.order.line",
        "program_id",
        string="PoS Order Lines",
        help="Order lines where this program is applied.",
    )
    promo_barcode = fields.Char(
        "Barcode",
        default=lambda self: self.env["coupon.coupon"]._generate_code(),
        help="A technical field used as an alternative to the promo_code. "
        "This is automatically generated when promo_code is changed.",
    )
    pos_order_ids = fields.Many2many(
        "pos.order", help="The PoS orders where this program is applied.", copy=False
    )
    pos_order_count = fields.Integer(
        "PoS Order Count", compute="_compute_pos_order_count"
    )
    valid_product_ids = fields.Many2many(
        "product.product",
        "Valid Products",
        compute="_compute_valid_product_ids",
        help="These are the products that are valid in this program.",
    )
    valid_partner_ids = fields.Many2many(
        "res.partner",
        "Valid Partners",
        compute="_compute_valid_partner_ids",
        help="These are the partners that can avail this program.",
    )

    @api.depends("pos_order_ids")
    def _compute_pos_order_count(self):
        for program in self:
            program.pos_order_count = len(program.pos_order_ids)

    def write(self, vals):
        if "promo_code" in vals:
            vals.update({"promo_barcode": self.env["coupon.coupon"]._generate_code()})
        return super(CouponProgram, self).write(vals)

    def action_view_pos_orders(self):
        self.ensure_one()
        return {
            "name": _("PoS Orders"),
            "view_mode": "tree,form",
            "res_model": "pos.order",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", self.pos_order_ids.ids)],
            "context": dict(self._context, create=False),
        }

    @api.depends("rule_products_domain")
    def _compute_valid_product_ids(self):
        domain_products = {}
        for program in self:
            product_ids = domain_products.get(program.rule_products_domain)
            if product_ids is None:
                domain = ast.literal_eval(program.rule_products_domain) if program.rule_products_domain else []
                product_ids = self.env["product.product"].search(domain, order="id").ids
                domain_products[program.rule_products_domain] = product_ids
            program.valid_product_ids = product_ids

    @api.depends("rule_partners_domain")
    def _compute_valid_partner_ids(self):
        domain_partners = {}
        for program in self:
            partner_ids = []
            if program.rule_partners_domain and program.rule_partners_domain != "[]":
                partner_ids = domain_partners.get(program.rule_partners_domain)
                if partner_ids is None:
                    domain = ast.literal_eval(program.rule_partners_domain)
                    partner_ids = self.env["res.partner"].search(domain, order="id").ids
                    domain_partners[program.rule_partners_domain] = partner_ids
            program.valid_partner_ids = partner_ids

    @api.depends('pos_order_ids')
    def _compute_total_order_count(self):
        super(CouponProgram, self)._compute_total_order_count()
        for program in self:
            program.total_order_count += len(program.pos_order_ids)
