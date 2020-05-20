# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate


class SaleOrder(models.Model):
    _inherit = "sale.order"
    _populate_sizes = {"small": 100, "medium": 10000, "large": 20000}
    _populate_dependencies = ["res.partner", "res.company", "res.users", "product.pricelist"]

    def _populate_factories(self):
        company_ids = self.env.registry.populated_models["res.company"]
        partner_ids = self.env.registry.populated_models["res.partner"]
        user_ids = self.env.registry.populated_models["res.users"]
        pricelist_ids = self.env.registry.populated_models["product.pricelist"]

        def get_company_info(iterator, field_name, model_name):
            random = populate.Random("sale_order_company")
            for counter, values in enumerate(iterator):
                cid = values.get("company_id")
                valid_partner_ids = self.env["res.partner"].browse(partner_ids).filtered_domain([
                    ("company_id", "in", [cid, False])
                ]).ids
                # valid_user_ids = self.env["res.users"].browse(user_ids).filtered_domain([
                #     ("company_ids", "in", [cid])
                # ]) # It seems that the current db population doesn't put people in all companies
                valid_pricelist_ids = self.env["product.pricelist"].browse(pricelist_ids).filtered_domain([
                    ("company_id", "in", [cid, False])
                ]).ids
                values.update({
                    "partner_id": random.choice(valid_partner_ids),
                    "user_id": random.choice(user_ids),
                    "pricelist_id": random.choice(valid_pricelist_ids),
                })
                yield values

        return [
            ("company_id", populate.randomize(company_ids)),
            ("_company_limited_fields", get_company_info),
            ("require_payment", populate.randomize([True, False])),
            ("require_signature", populate.randomize([True, False])),
            ("state", populate.randomize(["draft", "sent", "sale"], [10,5,1])),
        ]


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    _populate_sizes = {"small": 1000, "medium": 50000, "large": 100000}
    _populate_dependencies = ["sale.order", "product.product"]

    def _populate_factories(self):
        order_ids = self.env.registry.populated_models["sale.order"]
        product_ids = self.env.registry.populated_models["product.product"]
        # If we want more advanced products with multiple variants
        # add a populate dependency on product template and the following lines
        # product_ids += self.env["product.product"].search([
        #     ('product_tmpl_id', 'in', self.env.registry.populated_models["product.template"])
        # ]).ids
        # Currently, all products have the unit uom as uom
        uom_id = self.env.ref('uom.product_uom_unit').id
        # def _get_display_type(iterator, field_name, model_name):
        #     random = populate.Random("sale_order_line_display_type")
        #     i = 0
        #     for counter, values in enumerate(iterator):
        #         if not random.getrandbits(5):
        #             i += 1
        #             yield dict(
        #                 order_id=values["order_id"],
        #                 display_type=random.choice(["line_section", "line_note"]),
        #                 name="Section/Note %i" %i,
        #             )
        #         yield values
        return [
            ("order_id", populate.randomize(order_ids)),
            ("product_id", populate.randomize(product_ids)),
            ("product_uom", populate.compute(lambda **kwargs: uom_id)), # Should be randomized when products uom is randomized
            ("product_uom_qty", populate.randint(1, 200)), # partner_invoice_id & partner_shipping_id ???
            # ("display_type", _get_display_type), # TODO sections & notes ?
        ]
