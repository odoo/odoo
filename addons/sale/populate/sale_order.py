# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models
from odoo.tools import populate, groupby

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"
    _populate_sizes = {"small": 100, "medium": 2_000, "large": 20_000}
    _populate_dependencies = ["res.partner", "res.company", "res.users", "product.pricelist"]

    def _populate_factories(self):
        company_ids = self.env.registry.populated_models["res.company"]

        def x_ids_by_company(recordset, with_false=True):
            x_by_company = dict(groupby(recordset, key=lambda x_record: x_record.company_id.id))
            if with_false:
                x_inter_company = self.env[recordset._name].concat(*x_by_company.get(False, []))
            else:
                x_inter_company = self.env[recordset._name]
            return {com: (self.env[recordset._name].concat(*x_records) | x_inter_company).ids for com, x_records in x_by_company.items() if com}

        partners_ids_by_company = x_ids_by_company(self.env["res.partner"].browse(self.env.registry.populated_models["res.partner"]))
        pricelist_ids_by_company = x_ids_by_company(self.env["product.pricelist"].browse(self.env.registry.populated_models["product.pricelist"]))
        user_ids_by_company = x_ids_by_company(self.env["res.users"].browse(self.env.registry.populated_models["res.users"]), with_false=False)

        def get_company_info(iterator, field_name, model_name):
            random = populate.Random("sale_order_company")
            for values in iterator:
                cid = values.get("company_id")
                valid_partner_ids = partners_ids_by_company[cid]
                valid_user_ids = user_ids_by_company[cid]
                valid_pricelist_ids = pricelist_ids_by_company[cid]
                values.update({
                    "partner_id": random.choice(valid_partner_ids),
                    "user_id": random.choice(valid_user_ids),
                    "pricelist_id": random.choice(valid_pricelist_ids),
                })
                yield values

        return [
            ("company_id", populate.randomize(company_ids)),
            ("_company_limited_fields", get_company_info),
            ("require_payment", populate.randomize([True, False])),
            ("require_signature", populate.randomize([True, False])),
        ]


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    _populate_sizes = {"small": 1_000, "medium": 50_000, "large": 100_000}
    _populate_dependencies = ["sale.order", "product.product"]

    def _populate(self, size):
        so_line = super()._populate(size)

        def confirm_sale_order(sample_ratio):
            # Confirm sample_ratio * 100 % of picking
            random = populate.Random('confirm_sale_order')
            order_ids = so_line.order_id.ids
            orders_to_confirm = self.env['sale.order'].browse(random.sample(order_ids, int(len(order_ids) * sample_ratio)))
            _logger.info("Confirm %d sale orders", len(orders_to_confirm))
            orders_to_confirm.action_confirm()
            return orders_to_confirm

        confirm_sale_order(0.50)

        return so_line

    def _populate_factories(self):
        order_ids = self.env.registry.populated_models["sale.order"]
        product_ids = self.env.registry.populated_models["product.product"]
        # If we want more advanced products with multiple variants
        # add a populate dependency on product template and the following lines
        if 'product.template' in self.env.registry.populated_models:
            product_ids += self.env["product.product"].search([
                ('product_tmpl_id', 'in', self.env.registry.populated_models["product.template"])
            ]).ids

        self.env['product.product'].browse(product_ids).read(['uom_id'])  # prefetch all uom_id

        def get_product_uom(values, counter, random):
            return self.env['product.product'].browse(values['product_id']).uom_id.id

        # TODO sections & notes (display_type & name)

        return [
            ("order_id", populate.randomize(order_ids)),
            ("product_id", populate.randomize(product_ids)),
            ("product_uom", populate.compute(get_product_uom)),
            ("product_uom_qty", populate.randint(1, 200)),
        ]
