# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate
from datetime import timedelta, date


class Pricelist(models.Model):
    _inherit = "product.pricelist"
    _populate_sizes = {"small": 20, "medium": 100, "large": 1_500}
    _populate_dependencies = ["res.company"]

    def _populate(self, size):

        # Reflect the settings with data created
        self.env['res.config.settings'].create({
            'group_product_pricelist': True,  # Activate pricelist
            'group_sale_pricelist': True,  # Activate advanced pricelist
        }).execute()

        return super()._populate(size)

    def _populate_factories(self):
        company_ids = self.env.registry.populated_models["res.company"]

        return [
            ("company_id", populate.iterate(company_ids + [False for i in range(len(company_ids))])),
            ("name", populate.constant('product_pricelist_{counter}')),
            ("currency_id", populate.randomize(self.env["res.currency"].search([("active", "=", True)]).ids)),
            ("sequence", populate.randomize([False] + [i for i in range(1, 101)])),
            ("discount_policy", populate.randomize(["with_discount", "without_discount"])),
            ("active", populate.randomize([True, False], [0.8, 0.2])),
        ]


class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"
    _populate_sizes = {"small": 500, "medium": 5_000, "large": 50_000}
    _populate_dependencies = ["product.product", "product.template", "product.pricelist"]

    def _populate_factories(self):
        pricelist_ids = self.env.registry.populated_models["product.pricelist"]
        product_ids = self.env.registry.populated_models["product.product"]
        p_tmpl_ids = self.env.registry.populated_models["product.template"]
        categ_ids = self.env.registry.populated_models["product.category"]

        def get_target_info(iterator, field_name, model_name):
            random = populate.Random("pricelist_target")
            for values in iterator:
                # If product population is updated to consider multi company
                # the company of product would have to be considered
                # for product_id & product_tmpl_id
                applied_on = values["applied_on"]
                if applied_on == "0_product_variant":
                    values["product_id"] = random.choice(product_ids)
                elif applied_on == "1_product":
                    values["product_tmpl_id"] = random.choice(p_tmpl_ids)
                elif applied_on == "2_product_category":
                    values["categ_id"] = random.choice(categ_ids)
                yield values

        def get_prices(iterator, field_name, model_name):
            random = populate.Random("pricelist_prices")
            for values in iterator:
                # Fixed price, percentage, formula
                compute_price = values["compute_price"]
                if compute_price == "fixed":
                    # base = "list_price" = default
                    # fixed_price
                    values["fixed_price"] = random.randint(1, 1000)
                elif compute_price == "percentage":
                    # base = "list_price" = default
                    # percent_price
                    values["percent_price"] = random.randint(1, 100)
                else:  # formula
                    # pricelist base not considered atm.
                    values["base"] = random.choice(["list_price", "standard_price"])
                    values["price_discount"] = random.randint(0, 100)
                    # price_min_margin, price_max_margin
                    # price_round ??? price_discount, price_surcharge
                yield values

        now = date.today()

        def get_date_start(values, counter, random):
            if random.random() > 0.5:  # 50 % of chance to have validation dates
                return now + timedelta(days=random.randint(-20, 20))
            else:
                False

        def get_date_end(values, counter, random):
            if values['date_start']:  # 50 % of chance to have validation dates
                return values['date_start'] + timedelta(days=random.randint(5, 100))
            else:
                False

        return [
            ("pricelist_id", populate.randomize(pricelist_ids)),
            ("applied_on", populate.randomize(
                ["3_global", "2_product_category", "1_product", "0_product_variant"],
                [5, 3, 2, 1],
            )),
            ("compute_price", populate.randomize(
                ["fixed", "percentage", "formula"],
                [5, 3, 1],
            )),
            ("_price", get_prices),
            ("_target", get_target_info),
            ("min_quantity", populate.randint(0, 50)),
            ("date_start", populate.compute(get_date_start)),
            ("date_end", populate.compute(get_date_end)),
        ]
