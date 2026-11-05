# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from unittest.mock import patch

from odoo import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.product.tests.common import ProductVariantsCommon
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged("post_install", "-at_install")
class TestVariantAvailability(HttpCase, ProductVariantsCommon, WebsiteSaleCommon):
    """Test the availability data reported by `_get_attribute_exclusions` for
    attribute value muting on the product page: sold-out combinations,
    deleted combinations, and no_variant value handling.

    Availability is controlled by patching `website._get_product_available_qty`
    rather than by creating stock.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # All attribute lines are created together so variants are generated
        # once; the sold-out variant is captured only after all lines exist.
        cls.sofa = cls.env["product.template"].create({
            "name": "Test Sofa",
            "type": "consu",
            "is_storable": True,
            "allow_out_of_stock_order": False,
            "website_published": True,
            "attribute_line_ids": [
                Command.create({
                    "attribute_id": cls.color_attribute.id,
                    "value_ids": [
                        Command.set((cls.color_attribute_red + cls.color_attribute_blue).ids)
                    ],
                }),
                Command.create({
                    "attribute_id": cls.size_attribute.id,
                    "value_ids": [Command.set((cls.size_attribute_s + cls.size_attribute_m).ids)],
                }),
                Command.create({
                    "attribute_id": cls.no_variant_attribute.id,
                    "value_ids": [Command.set(cls.no_variant_attribute.value_ids.ids)],
                }),
            ],
        })
        cls.sold_out_variant = cls._get_variant("blue", "S")

    @classmethod
    def _get_variant(cls, *value_names):
        return cls.sofa.product_variant_ids.filtered(
            lambda p: (
                set(
                    p.product_template_attribute_value_ids.product_attribute_value_id.mapped("name")
                )
                == set(value_names)
            )
        )

    def _get_exclusions(self, template=None):
        template = template if template is not None else self.sofa
        return template.with_context(website_id=self.website.id)._get_attribute_exclusions()

    def _get_sold_out_combinations(self):
        return self._get_exclusions()["sold_out_combinations"]

    def _patch_availability(self, sold_out_variants):
        """Patch the availability seam: `sold_out_variants` have no quantity
        available, every other product has plenty.
        """
        sold_out_ids = set(sold_out_variants.ids)

        def _get_product_available_qty(_website, product, **_kwargs):
            return 0 if product.id in sold_out_ids else 10

        return patch.object(
            self.registry["website"], "_get_product_available_qty", _get_product_available_qty
        )

    # === Sold-out combinations ===

    def test_only_the_sold_out_variant_combination_reported(self):
        with self._patch_availability(self.sold_out_variant):
            self.assertEqual(
                self._get_sold_out_combinations(),
                [tuple(self.sold_out_variant.product_template_attribute_value_ids.ids)],
            )

    def test_no_combination_reported_while_every_variant_is_available(self):
        with self._patch_availability(self.env["product.product"]):
            self.assertEqual(self._get_sold_out_combinations(), [])

    def test_every_combination_reported_when_every_variant_is_sold_out(self):
        with self._patch_availability(self.sofa.product_variant_ids):
            self.assertCountEqual(
                self._get_sold_out_combinations(),
                [
                    tuple(v.product_template_attribute_value_ids.ids)
                    for v in self.sofa.product_variant_ids
                ],
            )

    def test_no_sold_out_combination_reported_outside_website(self):
        self.assertEqual(
            self.sofa._get_attribute_exclusions()["sold_out_combinations"],
            [],
            "Outside a website context, no combination should be reported",
        )

    def test_no_sold_out_combination_reported_when_selling_out_of_stock(self):
        self.sofa.sudo().allow_out_of_stock_order = True
        self.assertEqual(
            self._get_sold_out_combinations(),
            [],
            "Products sellable when out of stock are never sold out",
        )

    def test_no_sold_out_combination_reported_when_not_storable(self):
        self.sofa.sudo().is_storable = False
        self.assertEqual(
            self._get_sold_out_combinations(), [], "Non-storable products are never sold out"
        )

    def test_attributeless_variant_not_reported(self):
        """A sold-out variant with no PTAVs must not produce an empty tuple,
        which would client-side match every hypothetical combination."""
        simple = (
            self
            .env["product.template"]
            .sudo()
            .create({
                "name": "Simple",
                "type": "consu",
                "is_storable": True,
                "allow_out_of_stock_order": False,
                "website_published": True,
            })
        )
        with self._patch_availability(simple.product_variant_ids):
            self.assertEqual(self._get_exclusions(simple)["sold_out_combinations"], [])

    # === Deleted combinations ===

    def _get_combination(self, variant):
        return tuple(sorted(variant.product_template_attribute_value_ids.ids))

    def _get_archived_combinations(self, template=None):
        return [
            tuple(sorted(combo))
            for combo in self._get_exclusions(template)["archived_combinations"]
        ]

    def test_no_deleted_combination_reported_while_every_combination_has_a_variant(self):
        self.assertEqual(self._get_archived_combinations(), [])

    def test_deleted_variant_reported_as_archived(self):
        deleted_combination = self._get_combination(self.sold_out_variant)
        self.sold_out_variant.sudo().unlink()
        self.assertEqual(self._get_archived_combinations(), [deleted_combination])

    def test_archived_variant_not_also_reported_as_deleted(self):
        self.sold_out_variant.sudo().action_archive()
        self.assertEqual(
            self._get_archived_combinations(), [self._get_combination(self.sold_out_variant)]
        )

    def test_missing_dynamic_variant_not_reported_as_deleted(self):
        template = (
            self
            .env["product.template"]
            .sudo()
            .create({
                "name": "Dyn Sofa",
                "type": "consu",
                "is_storable": True,
                "allow_out_of_stock_order": False,
                "website_published": True,
                "attribute_line_ids": [
                    Command.create({
                        "attribute_id": self.color_attribute.id,
                        "value_ids": [
                            Command.set((self.color_attribute_red + self.color_attribute_blue).ids)
                        ],
                    }),
                    Command.create({
                        "attribute_id": self.dynamic_attribute.id,
                        "value_ids": [Command.set(self.dynamic_attribute.value_ids.ids)],
                    }),
                ],
            })
        )
        self.assertEqual(self._get_archived_combinations(template), [])

    # === no_variant value handling ===

    def test_no_variant_ptav_ids_reported(self):
        """PTAVs of no_variant attributes are reported so the client can
        exclude them from variant-tuple comparisons."""
        exclusions = self._get_exclusions()
        option_ptavs = self.sofa.attribute_line_ids.filtered(
            lambda line: line.attribute_id == self.no_variant_attribute
        ).product_template_value_ids
        self.assertCountEqual(exclusions["no_variant_ptav_ids"], option_ptavs.ids)

    def test_sold_out_combinations_never_contain_no_variant_values(self):
        with self._patch_availability(self.sofa.product_variant_ids):
            exclusions = self._get_exclusions()
        ptav_ids = {ptav_id for combo in exclusions["sold_out_combinations"] for ptav_id in combo}
        self.assertFalse(ptav_ids & set(exclusions["no_variant_ptav_ids"]))

    def test_deleted_combinations_never_contain_no_variant_values(self):
        self._get_variant("red", "M").sudo().unlink()
        exclusions = self._get_exclusions()
        ptav_ids = {ptav_id for combo in exclusions["archived_combinations"] for ptav_id in combo}
        self.assertFalse(ptav_ids & set(exclusions["no_variant_ptav_ids"]))

    # === Shop page previewer ===

    def _get_previewed_availability(self, template=None, in_website=True):
        """Return the previewed values of a template as {value name: unavailable}."""
        template = template if template is not None else self.sofa
        if in_website:
            template = template.with_context(website_id=self.website.id)
        previewed = template._get_previewed_attribute_values().get(template.id, {})
        return {
            entry["ptav"].name: entry["unavailable"] for entry in previewed.get("ptavs_data", [])
        }

    def _create_single_attribute_template(self):
        """Create a storable template whose only attribute is previewed, so that each
        value maps to exactly one variant."""
        return (
            self
            .env["product.template"]
            .sudo()
            .create({
                "name": "Test Stool",
                "type": "consu",
                "is_storable": True,
                "allow_out_of_stock_order": False,
                "website_published": True,
                "attribute_line_ids": [
                    Command.create({
                        "attribute_id": self.size_attribute.id,
                        "value_ids": [
                            Command.set((self.size_attribute_s + self.size_attribute_m).ids)
                        ],
                    })
                ],
            })
        )

    def test_previewed_value_available_while_one_variant_is_in_stock(self):
        self.color_attribute.sudo().preview_variants = "hover"
        with self._patch_availability(self.sold_out_variant):
            self.assertEqual(self._get_previewed_availability(), {"red": False, "blue": False})

    def test_previewed_value_unavailable_when_all_its_variants_are_sold_out(self):
        self.color_attribute.sudo().preview_variants = "hover"
        blue_variants = self._get_variant("blue", "S") + self._get_variant("blue", "M")
        with self._patch_availability(blue_variants):
            self.assertEqual(self._get_previewed_availability(), {"red": False, "blue": True})

    def test_previewed_value_unavailable_when_its_only_variant_is_sold_out(self):
        stool = self._create_single_attribute_template()
        self.size_attribute.sudo().preview_variants = "visible"
        small_stool = stool.product_variant_ids.filtered(
            lambda p: p.product_template_attribute_value_ids.product_attribute_value_id.name == "S"
        )
        with self._patch_availability(small_stool):
            self.assertEqual(self._get_previewed_availability(stool), {"S": True, "M": False})

    def _exclude_every_blue_combination(self):
        """Preview the colors and exclude blue with every size.

        :return: the blue value.
        :rtype: product.template.attribute.value
        """
        self.color_attribute.sudo().preview_variants = "hover"
        blue = self.sofa.attribute_line_ids.product_template_value_ids.filtered(
            lambda ptav: ptav.name == "blue"
        )
        sizes = self.sofa.attribute_line_ids.filtered(
            lambda line: line.attribute_id == self.size_attribute
        ).product_template_value_ids
        blue.sudo().excluded_value_ids = [Command.set(sizes.ids)]
        return blue

    def test_excluding_every_combination_of_a_value_archives_its_variants(self):
        blue = self._exclude_every_blue_combination()
        self.assertFalse(blue.ptav_product_variant_ids)

    def test_previewed_value_dropped_when_all_its_combinations_are_excluded(self):
        self._exclude_every_blue_combination()
        with self._patch_availability(self.env["product.product"]):
            self.assertNotIn("blue", self._get_previewed_availability())

    def _exclude_blue_small(self):
        """Preview the colors and exclude (blue, S), so (blue, M) is the only
        variant left for blue."""
        self.color_attribute.sudo().preview_variants = "hover"
        blue = self.sofa.attribute_line_ids.product_template_value_ids.filtered(
            lambda ptav: ptav.name == "blue"
        )
        small = self.sofa.attribute_line_ids.product_template_value_ids.filtered(
            lambda ptav: ptav.name == "S"
        )
        blue.sudo().excluded_value_ids = [Command.set(small.ids)]

    def test_previewed_value_available_while_its_variant_left_after_exclusion_is_in_stock(self):
        self._exclude_blue_small()
        with self._patch_availability(self.env["product.product"]):
            self.assertEqual(self._get_previewed_availability(), {"red": False, "blue": False})

    def test_previewed_value_unavailable_when_its_variant_left_after_exclusion_is_sold_out(self):
        self._exclude_blue_small()
        with self._patch_availability(self._get_variant("blue", "M")):
            self.assertEqual(self._get_previewed_availability(), {"red": False, "blue": True})

    def test_previewed_values_available_when_selling_out_of_stock(self):
        self.color_attribute.sudo().preview_variants = "hover"
        self.sofa.sudo().allow_out_of_stock_order = True
        with self._patch_availability(self.sofa.product_variant_ids):
            self.assertEqual(self._get_previewed_availability(), {"red": False, "blue": False})

    def test_previewed_values_available_when_not_storable(self):
        self.color_attribute.sudo().preview_variants = "hover"
        self.sofa.sudo().is_storable = False
        with self._patch_availability(self.sofa.product_variant_ids):
            self.assertEqual(self._get_previewed_availability(), {"red": False, "blue": False})

    def test_previewed_values_available_outside_website(self):
        self.color_attribute.sudo().preview_variants = "hover"
        with self._patch_availability(self.sofa.product_variant_ids):
            self.assertEqual(
                self._get_previewed_availability(in_website=False),
                {"red": False, "blue": False},
                "Outside a website context, no availability can be computed",
            )

    def _preview_sofa_and_stool(self):
        """Preview the sofa and a stool together, as a shop page does.

        :return: the stool, and the variants of each `_filter_sold_out` call.
        :rtype: tuple(product.template, list(product.product))
        """
        self.color_attribute.sudo().preview_variants = "hover"
        self.size_attribute.sudo().preview_variants = "visible"
        stool = self._create_single_attribute_template()
        templates = (self.sofa + stool).with_context(website_id=self.website.id)

        calls = []
        filter_sold_out = self.registry["product.product"]._filter_sold_out

        def _filter_sold_out(variants):
            calls.append(variants)
            return filter_sold_out(variants)

        with (
            self._patch_availability(self.sold_out_variant),
            patch.object(self.registry["product.product"], "_filter_sold_out", _filter_sold_out),
        ):
            templates._get_previewed_attribute_values()
        return stool, calls

    def test_shop_page_checks_previewed_availability_with_one_stock_query(self):
        _stool, calls = self._preview_sofa_and_stool()
        self.assertEqual(len(calls), 1)

    def test_shop_page_checks_the_variants_of_every_previewed_product(self):
        stool, calls = self._preview_sofa_and_stool()
        self.assertEqual(
            self.env["product.product"].concat(*calls),
            self.sofa.product_variant_ids + stool.product_variant_ids,
        )

    # === Landing combination ===

    def _resolve_combination(self, *requested_names, template=None):
        """Resolve the combination the product page lands on when the URL asks for the
        given values, the way `_prepare_product_values` does.

        :return: the names of the resolved values.
        :rtype: set(str)
        """
        template = template if template is not None else self.sofa
        template = template.with_context(website_id=self.website.id)
        if requested_names:
            combination = template.attribute_line_ids.mapped(
                lambda ptal: (
                    ptal.product_template_value_ids.filtered(
                        lambda ptav: ptav.ptav_active and ptav.name in requested_names
                    )[:1]
                    or ptal.product_template_value_ids.filtered(
                        lambda ptav: ptav.ptav_active and ptal.attribute_id.display_type != "multi"
                    )[:1]
                )
            )
            necessary_values = combination.filtered(lambda ptav: ptav.name in requested_names)
        else:
            combination = template._get_first_possible_combination()
            necessary_values = self.env["product.template.attribute.value"]
        return set(
            template._get_available_combination(combination, necessary_values).mapped("name")
        )

    def test_default_variant_kept_when_it_can_be_bought(self):
        with self._patch_availability(self.sold_out_variant):
            self.assertEqual(self._resolve_combination("M"), {"red", "M", "extra"})

    def test_completion_moves_to_a_variant_that_can_be_bought(self):
        with self._patch_availability(self._get_variant("red", "S")):
            self.assertEqual(self._resolve_combination("S"), {"blue", "S", "extra"})

    def test_requested_value_kept_while_completion_moves_to_a_buyable_variant(self):
        with self._patch_availability(self._get_variant("blue", "S")):
            self.assertEqual(self._resolve_combination("blue"), {"blue", "M", "extra"})

    def test_completion_kept_when_nothing_can_be_bought(self):
        small_variants = self._get_variant("red", "S") + self._get_variant("blue", "S")
        with self._patch_availability(small_variants):
            self.assertEqual(self._resolve_combination("S"), {"red", "S", "extra"})

    def test_completion_moves_when_the_default_variant_is_archived(self):
        self._get_variant("red", "S").sudo().active = False
        with self._patch_availability(self.env["product.product"]):
            self.assertEqual(self._resolve_combination("S"), {"blue", "S", "extra"})

    def test_completion_moves_when_the_default_variant_is_deleted(self):
        self._get_variant("red", "S").sudo().unlink()
        with self._patch_availability(self.env["product.product"]):
            self.assertEqual(self._resolve_combination("S"), {"blue", "S", "extra"})

    def test_completion_untouched_when_selling_out_of_stock(self):
        self.sofa.sudo().allow_out_of_stock_order = True
        with self._patch_availability(self.sofa.product_variant_ids):
            self.assertEqual(self._resolve_combination("S"), {"red", "S", "extra"})

    def test_completion_untouched_when_not_storable(self):
        self.sofa.sudo().is_storable = False
        with self._patch_availability(self.sofa.product_variant_ids):
            self.assertEqual(self._resolve_combination("S"), {"red", "S", "extra"})

    def test_default_moves_without_requested_values(self):
        """Opening the product straight from the tile pins nothing, so the whole default
        is free to move onto the first variant that can be bought."""
        with self._patch_availability(self._get_variant("red", "S")):
            self.assertEqual(self._resolve_combination(), {"blue", "S", "extra"})

    def test_default_untouched_without_requested_values_when_all_sold_out(self):
        """Nothing to move to: the plain default is kept so the customer still gets the
        out-of-stock message and its notification form."""
        with self._patch_availability(self.sofa.product_variant_ids):
            self.assertEqual(self._resolve_combination(), {"red", "S", "extra"})

    def test_no_variant_values_survive_the_move(self):
        """Ticked no_variant values belong to no variant, so they are carried over as they are."""
        with self._patch_availability(self._get_variant("red", "S")):
            self.assertIn("second", self._resolve_combination("S", "second"))

    # === Shop page preview image ===

    def _get_previewed_variant_ids(self, template=None):
        """Return the previewed values of a template as {value name: previewed variant id}."""
        template = template if template is not None else self.sofa
        template = template.with_context(website_id=self.website.id)
        previewed = template._get_previewed_attribute_values().get(template.id, {})
        return {
            entry["ptav"].name: int(entry["variant_image_url"].split("/")[4])
            for entry in previewed.get("ptavs_data", [])
        }

    def test_previewed_image_is_the_first_variant_by_default(self):
        self.size_attribute.sudo().preview_variants = "visible"
        small_variants = self._get_variant("red", "S") + self._get_variant("blue", "S")
        with self._patch_availability(self.env["product.product"]):
            self.assertEqual(self._get_previewed_variant_ids()["S"], min(small_variants.ids))

    def test_previewed_image_follows_the_variant_landed_on(self):
        self.size_attribute.sudo().preview_variants = "visible"
        with self._patch_availability(self._get_variant("red", "S")):
            self.assertEqual(
                self._get_previewed_variant_ids()["S"], self._get_variant("blue", "S").id
            )

    def test_previewed_image_kept_when_the_value_is_unavailable(self):
        self.size_attribute.sudo().preview_variants = "visible"
        small_variants = self._get_variant("red", "S") + self._get_variant("blue", "S")
        with self._patch_availability(small_variants):
            self.assertEqual(self._get_previewed_variant_ids()["S"], min(small_variants.ids))

    # === Template availability ===

    def test_template_not_sold_out_when_only_its_first_variant_is_sold_out(self):
        sofa = self.sofa.with_context(website_id=self.website.id)
        with self._patch_availability(sofa.product_variant_id):
            self.assertFalse(sofa._is_sold_out())

    def test_template_sold_out_when_no_variant_is_left(self):
        sofa = self.sofa.with_context(website_id=self.website.id)
        with self._patch_availability(sofa.product_variant_ids):
            self.assertTrue(sofa._is_sold_out())

    # === Ribbon ===

    def _out_of_stock_ribbon(self):
        """Return the standard ribbon, set to the automatic out-of-stock assignment.

        Written on the standard record rather than created: only one ribbon may carry a
        given automatic assignment, and `website_sale_stock` demo data already uses it.
        Sudoed: the test user is a salesman, and ribbons are manager-only.

        Passed back to be handed over as the only automatic ribbon, so that no other
        assignment can answer in its place.
        """
        ribbon = self.env.ref("website_sale.out_of_stock_ribbon")
        ribbon.sudo().assign = "out_of_stock"
        return ribbon

    def _get_sold_out_variant_ribbon(self, ribbon, is_combination_possible):
        """Return the ribbon of the sold-out variant when its combination is possible or not.

        An impossible combination still resolves to a variant, an archived or excluded one.
        """
        sofa = self.sofa.with_context(website_id=self.website.id)
        with self._patch_availability(sofa.product_variant_ids):
            return sofa._get_ribbon(
                price_vals={"is_combination_possible": is_combination_possible},
                auto_assign_ribbons=ribbon,
                variant=self.sold_out_variant,
            )

    def test_out_of_stock_ribbon_shown_for_a_possible_sold_out_combination(self):
        ribbon = self._out_of_stock_ribbon()
        self.assertEqual(
            self._get_sold_out_variant_ribbon(ribbon, is_combination_possible=True), ribbon
        )

    def test_out_of_stock_ribbon_skipped_for_an_impossible_combination(self):
        ribbon = self._out_of_stock_ribbon()
        self.assertFalse(self._get_sold_out_variant_ribbon(ribbon, is_combination_possible=False))

    def test_out_of_stock_ribbon_skipped_while_another_variant_sells(self):
        """The shop tile stands for the product, not for the variant it happens to show:
        it must not be ribboned out of stock while another variant can be bought."""
        ribbon = self._out_of_stock_ribbon()
        sofa = self.sofa.with_context(website_id=self.website.id)
        with self._patch_availability(sofa.product_variant_id):
            self.assertFalse(sofa._get_ribbon(auto_assign_ribbons=ribbon))

    def test_out_of_stock_ribbon_shown_when_no_variant_is_left(self):
        ribbon = self._out_of_stock_ribbon()
        sofa = self.sofa.with_context(website_id=self.website.id)
        with self._patch_availability(sofa.product_variant_ids):
            self.assertEqual(sofa._get_ribbon(auto_assign_ribbons=ribbon), ribbon)

    def test_out_of_stock_ribbon_shown_for_the_sold_out_variant_displayed_on_the_product_page(self):
        ribbon = self._out_of_stock_ribbon()
        sofa = self.sofa.with_context(website_id=self.website.id)
        with self._patch_availability(sofa.product_variant_id):
            self.assertEqual(
                sofa._get_ribbon(auto_assign_ribbons=ribbon, variant=sofa.product_variant_id),
                ribbon,
            )

    # === Product page CTA ===

    def _get_add_to_cart_classes(self):
        """Return the classes the product page is served with on its add-to-cart wrapper."""
        page = self.url_open(self.sofa.website_url).text
        return re.search(r'id="add_to_cart_wrap"\s+class="([^"]*)"', page).group(1).split()

    def test_sold_out_page_is_served_with_the_cta_already_hidden(self):
        """The landing combination is known server-side, so the page must not be served
        buyable and then corrected by the load-time round trip."""
        with self._patch_availability(self.sofa.product_variant_ids):
            self.assertIn("d-none", self._get_add_to_cart_classes())

    def test_buyable_page_is_served_with_the_cta_shown(self):
        with self._patch_availability(self.env["product.product"]):
            self.assertNotIn("d-none", self._get_add_to_cart_classes())

    # === Tour ===

    def test_sold_out_variant_muted_tour(self):
        """The sold-out neighbor value is struck through, follows selection,
        and survives no_variant option toggling."""
        with self._patch_availability(self.sold_out_variant):
            self.start_tour(self.sofa.website_url, "website_sale.variant_availability")

    def test_shop_click_lands_on_a_buyable_variant_tour(self):
        """Clicking a previewed value that isn't muted opens a variant that can be bought,
        not the sold-out one the default completion points at."""
        self.color_attribute.sudo().preview_variants = "visible"
        with self._patch_availability(self._get_variant("red", "S")):
            self.start_tour(
                "/shop?search=Test+Sofa", "website_sale.shop_variant_availability_landing"
            )

    def test_shop_tile_click_lands_on_a_buyable_variant_tour(self):
        """Opening the product from the tile pins no value, so the whole default moves onto
        a buyable variant, and the tile isn't ribboned while other variants sell."""
        self.env.ref("website_sale.out_of_stock_ribbon").sudo().assign = "out_of_stock"
        with self._patch_availability(self._get_variant("red", "S")):
            self.start_tour(
                "/shop?search=Test+Sofa", "website_sale.shop_variant_availability_tile_landing"
            )

    def test_unavailable_previewed_value_muted_on_shop_tour(self):
        """On /shop, a previewed value with nothing left to buy is muted, while a value
        with stock left isn't, and the muted one is still a link."""
        self.color_attribute.sudo().preview_variants = "visible"
        blue_variants = self._get_variant("blue", "S") + self._get_variant("blue", "M")
        with self._patch_availability(blue_variants):
            self.start_tour("/shop?search=Test+Sofa", "website_sale.shop_variant_availability")
