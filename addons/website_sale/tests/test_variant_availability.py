# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from unittest.mock import patch

from odoo import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged("post_install", "-at_install")
class TestVariantAvailability(HttpCase, WebsiteSaleCommon):
    """Test the availability data reported by `_get_attribute_exclusions` for
    attribute value muting on the product page: sold-out combinations,
    existing (non-deleted) combinations, and no_variant value handling.

    Availability is controlled by patching `website._get_product_available_qty`
    rather than by creating stock.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.material_attribute = cls.env["product.attribute"].create({
            "name": "Material",
            "value_ids": [
                Command.create({"name": "Wood", "sequence": 1}),
                Command.create({"name": "Steel", "sequence": 2}),
            ],
        })
        cls.color_attribute_2 = cls.env["product.attribute"].create({
            "name": "Color",
            "value_ids": [
                Command.create({"name": "White", "sequence": 1}),
                Command.create({"name": "Black", "sequence": 2}),
            ],
        })
        cls.options_attribute = cls.env["product.attribute"].create({
            "name": "Options",
            "create_variant": "no_variant",
            "display_type": "multi",
            "value_ids": [
                Command.create({"name": "Drawers", "sequence": 1}),
                Command.create({"name": "Shelves", "sequence": 2}),
            ],
        })
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
                    "attribute_id": cls.material_attribute.id,
                    "value_ids": [Command.set(cls.material_attribute.value_ids.ids)],
                }),
                Command.create({
                    "attribute_id": cls.color_attribute_2.id,
                    "value_ids": [Command.set(cls.color_attribute_2.value_ids.ids)],
                }),
                Command.create({
                    "attribute_id": cls.options_attribute.id,
                    "value_ids": [Command.set(cls.options_attribute.value_ids.ids)],
                }),
            ],
        })
        cls.sold_out_variant = cls._get_variant("Steel", "White")

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

    def test_sold_out_combinations_values(self):
        """The sold-out variant is reported as its PTAV combination, others are not."""
        with self._patch_availability(self.sold_out_variant):
            self.assertEqual(
                self._get_sold_out_combinations(),
                [tuple(self.sold_out_variant.product_template_attribute_value_ids.ids)],
            )

    def test_sold_out_combinations_follow_availability(self):
        """The reported set reflects current availability, not a stored state."""
        with self._patch_availability(self.env["product.product"]):
            self.assertEqual(self._get_sold_out_combinations(), [])
        with self._patch_availability(self.sofa.product_variant_ids):
            self.assertCountEqual(
                self._get_sold_out_combinations(),
                [
                    tuple(v.product_template_attribute_value_ids.ids)
                    for v in self.sofa.product_variant_ids
                ],
            )

    def test_outside_website_no_combination(self):
        self.assertEqual(
            self.sofa._get_attribute_exclusions()["sold_out_combinations"],
            [],
            "Outside a website context, no combination should be reported",
        )

    def test_allow_oos_never_sold_out(self):
        self.sofa.sudo().allow_out_of_stock_order = True
        self.assertEqual(
            self._get_sold_out_combinations(),
            [],
            "Products sellable when out of stock are never sold out",
        )

    def test_non_storable_never_sold_out(self):
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

    # === Existing combinations (deleted-variant detection) ===

    def test_existing_combinations_reported(self):
        """All variant combinations are reported in Instantly mode."""
        self.assertCountEqual(
            self._get_exclusions()["existing_combinations"],
            [
                tuple(v.product_template_attribute_value_ids.ids)
                for v in self.sofa.product_variant_ids
            ],
        )

    def test_deleted_variant_missing_from_existing(self):
        """A deleted variant's combination disappears from the existing list."""
        deleted_combination = tuple(self.sold_out_variant.product_template_attribute_value_ids.ids)
        self.sold_out_variant.sudo().unlink()
        self.assertNotIn(deleted_combination, self._get_exclusions()["existing_combinations"])

    def test_existing_combinations_none_when_dynamic(self):
        """The inference is disabled (None) when any attribute creates variants
        dynamically: a missing variant is then normal, not a deletion."""
        dyn_attribute = (
            self
            .env["product.attribute"]
            .sudo()
            .create({
                "name": "Dynamic Option",
                "create_variant": "dynamic",
                "value_ids": [
                    Command.create({"name": "A", "sequence": 1}),
                    Command.create({"name": "B", "sequence": 2}),
                ],
            })
        )
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
                        "attribute_id": self.material_attribute.id,
                        "value_ids": [Command.set(self.material_attribute.value_ids.ids)],
                    }),
                    Command.create({
                        "attribute_id": dyn_attribute.id,
                        "value_ids": [Command.set(dyn_attribute.value_ids.ids)],
                    }),
                ],
            })
        )
        self.assertIsNone(self._get_exclusions(template)["existing_combinations"])

    def test_existing_combinations_kept_with_no_variant(self):
        """no_variant attributes must not disable the inference: the sofa has
        a no_variant Options line and still reports a real list."""
        self.assertIsInstance(self._get_exclusions()["existing_combinations"], list)

    # === no_variant value handling ===

    def test_no_variant_ptav_ids_reported(self):
        """PTAVs of no_variant attributes are reported so the client can
        exclude them from variant-tuple comparisons."""
        exclusions = self._get_exclusions()
        option_ptavs = self.sofa.attribute_line_ids.filtered(
            lambda line: line.attribute_id == self.options_attribute
        ).product_template_value_ids
        self.assertCountEqual(exclusions["no_variant_ptav_ids"], option_ptavs.ids)

    def test_variant_tuples_never_contain_no_variant_ptavs(self):
        """Sold-out and existing tuples are variant-sized: no_variant PTAVs
        (here: the Options values) never appear in them."""
        no_variant_ids = set(self._get_exclusions()["no_variant_ptav_ids"])
        with self._patch_availability(self.sofa.product_variant_ids):
            exclusions = self._get_exclusions()
        for combo in exclusions["sold_out_combinations"] + exclusions["existing_combinations"]:
            self.assertEqual(len(combo), 2)
            self.assertFalse(set(combo) & no_variant_ids)

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
                        "attribute_id": self.color_attribute_2.id,
                        "value_ids": [Command.set(self.color_attribute_2.value_ids.ids)],
                    })
                ],
            })
        )

    def test_previewed_value_available_while_one_variant_is_in_stock(self):
        """With several attributes, a value stays available as long as one of its
        combinations can be bought."""
        self.material_attribute.sudo().preview_variants = "hover"
        with self._patch_availability(self.sold_out_variant):
            self.assertEqual(self._get_previewed_availability(), {"Wood": False, "Steel": False})

    def test_previewed_value_unavailable_when_all_its_variants_are_sold_out(self):
        self.material_attribute.sudo().preview_variants = "hover"
        steel_variants = self._get_variant("Steel", "White") + self._get_variant("Steel", "Black")
        with self._patch_availability(steel_variants):
            self.assertEqual(self._get_previewed_availability(), {"Wood": False, "Steel": True})

    def test_previewed_value_unavailable_with_a_single_attribute(self):
        """With a single attribute a value is one variant, so it is muted as soon as
        that variant is sold out."""
        stool = self._create_single_attribute_template()
        self.color_attribute_2.sudo().preview_variants = "visible"
        white_stool = stool.product_variant_ids.filtered(
            lambda p: (
                p.product_template_attribute_value_ids.product_attribute_value_id.name == "White"
            )
        )
        with self._patch_availability(white_stool):
            self.assertEqual(
                self._get_previewed_availability(stool), {"White": True, "Black": False}
            )

    def test_previewed_value_dropped_when_all_its_combinations_are_excluded(self):
        """Excluding every combination of a value archives its variants, so the value
        leaves the previewer altogether instead of being muted. Only Wood is left, and a
        single value isn't previewed at all."""
        self.material_attribute.sudo().preview_variants = "hover"
        steel = self.sofa.attribute_line_ids.product_template_value_ids.filtered(
            lambda ptav: ptav.name == "Steel"
        )
        colors = self.sofa.attribute_line_ids.filtered(
            lambda line: line.attribute_id == self.color_attribute_2
        ).product_template_value_ids
        steel.sudo().excluded_value_ids = [Command.set(colors.ids)]
        self.assertFalse(steel.ptav_product_variant_ids)
        with self._patch_availability(self.env["product.product"]):
            self.assertEqual(self._get_previewed_availability(), {})

    def test_previewed_availability_ignores_excluded_combinations(self):
        """Availability is decided on the variants that are left: (Steel, White) is
        excluded, so Steel is muted as soon as (Steel, Black) is sold out."""
        self.material_attribute.sudo().preview_variants = "hover"
        steel = self.sofa.attribute_line_ids.product_template_value_ids.filtered(
            lambda ptav: ptav.name == "Steel"
        )
        white = self.sofa.attribute_line_ids.product_template_value_ids.filtered(
            lambda ptav: ptav.name == "White"
        )
        steel.sudo().excluded_value_ids = [Command.set(white.ids)]
        with self._patch_availability(self.env["product.product"]):
            self.assertEqual(self._get_previewed_availability(), {"Wood": False, "Steel": False})
        with self._patch_availability(self._get_variant("Steel", "Black")):
            self.assertEqual(self._get_previewed_availability(), {"Wood": False, "Steel": True})

    def test_previewed_values_available_when_selling_out_of_stock(self):
        self.material_attribute.sudo().preview_variants = "hover"
        self.sofa.sudo().allow_out_of_stock_order = True
        with self._patch_availability(self.sofa.product_variant_ids):
            self.assertEqual(self._get_previewed_availability(), {"Wood": False, "Steel": False})

    def test_previewed_values_available_when_not_storable(self):
        self.material_attribute.sudo().preview_variants = "hover"
        self.sofa.sudo().is_storable = False
        with self._patch_availability(self.sofa.product_variant_ids):
            self.assertEqual(self._get_previewed_availability(), {"Wood": False, "Steel": False})

    def test_previewed_values_available_outside_website(self):
        self.material_attribute.sudo().preview_variants = "hover"
        with self._patch_availability(self.sofa.product_variant_ids):
            self.assertEqual(
                self._get_previewed_availability(in_website=False),
                {"Wood": False, "Steel": False},
                "Outside a website context, no availability can be computed",
            )

    def test_previewed_availability_is_computed_in_one_batch(self):
        """Availability must be resolved once for the whole recordset: a shop page
        renders many products and mustn't pay one stock query per product."""
        self.material_attribute.sudo().preview_variants = "hover"
        self.color_attribute_2.sudo().preview_variants = "visible"
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

        self.assertEqual(len(calls), 1)
        self.assertEqual(
            calls[0],
            self.sofa.product_variant_ids + stool.product_variant_ids,
            "The variants of every previewed value are checked in a single call",
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
                    or ptal.product_template_value_ids.filtered("ptav_active")[:1]
                )
            )
            necessary_values = combination.filtered(lambda ptav: ptav.name in requested_names)
        else:
            combination = template._get_first_possible_combination()
            necessary_values = self.env["product.template.attribute.value"]
        return set(
            template._get_available_combination(combination, necessary_values).mapped("name")
        )

    def test_default_completion_kept_when_it_can_be_bought(self):
        """Nothing to fix: the first value of each unasked line is buyable."""
        with self._patch_availability(self.sold_out_variant):
            self.assertEqual(self._resolve_combination("Black"), {"Wood", "Black", "Drawers"})

    def test_completion_moves_to_a_variant_that_can_be_bought(self):
        """(White, Wood) is the default completion of White but is sold out, so White
        lands on (White, Steel) instead."""
        with self._patch_availability(self._get_variant("Wood", "White")):
            self.assertEqual(self._resolve_combination("White"), {"Steel", "White", "Drawers"})

    def test_requested_values_are_never_moved(self):
        """Only the completed values move: asking for Steel keeps Steel and changes the
        color instead."""
        with self._patch_availability(self._get_variant("Steel", "White")):
            self.assertEqual(self._resolve_combination("Steel"), {"Steel", "Black", "Drawers"})

    def test_completion_kept_when_nothing_can_be_bought(self):
        """With every White variant sold out, the default completion is kept so the
        customer still gets the out-of-stock message and its notification form."""
        white_variants = self._get_variant("Wood", "White") + self._get_variant("Steel", "White")
        with self._patch_availability(white_variants):
            self.assertEqual(self._resolve_combination("White"), {"Wood", "White", "Drawers"})

    def test_completion_moves_when_the_default_variant_is_archived(self):
        self._get_variant("Wood", "White").sudo().active = False
        with self._patch_availability(self.env["product.product"]):
            self.assertEqual(self._resolve_combination("White"), {"Steel", "White", "Drawers"})

    def test_completion_moves_when_the_default_variant_is_deleted(self):
        self._get_variant("Wood", "White").sudo().unlink()
        with self._patch_availability(self.env["product.product"]):
            self.assertEqual(self._resolve_combination("White"), {"Steel", "White", "Drawers"})

    def test_completion_untouched_when_selling_out_of_stock(self):
        self.sofa.sudo().allow_out_of_stock_order = True
        with self._patch_availability(self.sofa.product_variant_ids):
            self.assertEqual(self._resolve_combination("White"), {"Wood", "White", "Drawers"})

    def test_completion_untouched_when_not_storable(self):
        self.sofa.sudo().is_storable = False
        with self._patch_availability(self.sofa.product_variant_ids):
            self.assertEqual(self._resolve_combination("White"), {"Wood", "White", "Drawers"})

    def test_default_moves_without_requested_values(self):
        """Opening the product straight from the tile pins nothing, so the whole default
        is free to move onto the first variant that can be bought.

        The default combination ticks no `multi` value, hence no "Drawers".
        """
        with self._patch_availability(self._get_variant("Wood", "White")):
            self.assertEqual(self._resolve_combination(), {"Wood", "Black"})

    def test_default_untouched_without_requested_values_when_all_sold_out(self):
        """Nothing to move to: the plain default is kept so the customer still gets the
        out-of-stock message and its notification form."""
        with self._patch_availability(self.sofa.product_variant_ids):
            self.assertEqual(self._resolve_combination(), {"Wood", "White"})

    def test_no_variant_values_survive_the_move(self):
        """no_variant values belong to no variant, so they are carried over as they are."""
        with self._patch_availability(self._get_variant("Wood", "White")):
            self.assertIn("Drawers", self._resolve_combination("White"))

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
        self.color_attribute_2.sudo().preview_variants = "visible"
        white_variants = self._get_variant("Wood", "White") + self._get_variant("Steel", "White")
        with self._patch_availability(self.env["product.product"]):
            self.assertEqual(self._get_previewed_variant_ids()["White"], min(white_variants.ids))

    def test_previewed_image_follows_the_variant_landed_on(self):
        """The tile previews the variant the value now links to, not a sold-out one."""
        self.color_attribute_2.sudo().preview_variants = "visible"
        with self._patch_availability(self._get_variant("Wood", "White")):
            self.assertEqual(
                self._get_previewed_variant_ids()["White"], self._get_variant("Steel", "White").id
            )

    def test_previewed_image_kept_when_the_value_is_unavailable(self):
        """A muted value has no buyable variant left to preview, so it keeps the first one."""
        self.color_attribute_2.sudo().preview_variants = "visible"
        white_variants = self._get_variant("Wood", "White") + self._get_variant("Steel", "White")
        with self._patch_availability(white_variants):
            self.assertEqual(self._get_previewed_variant_ids()["White"], min(white_variants.ids))

    # === Template availability ===

    def test_template_not_sold_out_while_one_variant_sells(self):
        """A template stands for all of its variants, so one buyable variant is enough,
        whichever it is: the first one being sold out proves nothing."""
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

    def test_out_of_stock_ribbon_skipped_for_an_unavailable_combination(self):
        """A combination without a variant is unavailable, not out of stock: the automatic
        ribbon must not fall back on the template's first variant to describe it."""
        ribbon = self._out_of_stock_ribbon()
        sofa = self.sofa.with_context(website_id=self.website.id)
        with self._patch_availability(sofa.product_variant_ids):
            self.assertEqual(
                sofa._get_ribbon(auto_assign_ribbons=ribbon, variant=self.sold_out_variant),
                ribbon,
                "A sold-out variant still gets the out-of-stock ribbon",
            )
            self.assertFalse(
                sofa._get_ribbon(auto_assign_ribbons=ribbon, variant=self.env["product.product"]),
                "An unavailable combination gets no ribbon at all",
            )
            self.assertEqual(
                sofa._get_ribbon(auto_assign_ribbons=ribbon),
                ribbon,
                "Callers that don't know the variant still fall back on the first one",
            )

    def test_out_of_stock_ribbon_skipped_for_an_impossible_combination(self):
        """An impossible combination still resolves to a variant, an archived or excluded one:
        it is unavailable, not out of stock, so the ribbon must not describe it as such."""
        ribbon = self._out_of_stock_ribbon()
        sofa = self.sofa.with_context(website_id=self.website.id)
        with self._patch_availability(sofa.product_variant_ids):
            self.assertEqual(
                sofa._get_ribbon(
                    price_vals={"is_combination_possible": True},
                    auto_assign_ribbons=ribbon,
                    variant=self.sold_out_variant,
                ),
                ribbon,
            )
            self.assertFalse(
                sofa._get_ribbon(
                    price_vals={"is_combination_possible": False},
                    auto_assign_ribbons=ribbon,
                    variant=self.sold_out_variant,
                ),
                "No out-of-stock ribbon for a combination that can't be configured",
            )

    def test_out_of_stock_ribbon_skipped_while_another_variant_sells(self):
        """The shop tile stands for the product, not for the variant it happens to show:
        it must not be ribboned out of stock while another variant can be bought."""
        ribbon = self._out_of_stock_ribbon()
        sofa = self.sofa.with_context(website_id=self.website.id)
        with self._patch_availability(sofa.product_variant_id):
            self.assertFalse(
                sofa._get_ribbon(
                    auto_assign_ribbons=ribbon, variant=sofa.product_variant_id, for_template=True
                )
            )

    def test_out_of_stock_ribbon_shown_when_no_variant_is_left(self):
        ribbon = self._out_of_stock_ribbon()
        sofa = self.sofa.with_context(website_id=self.website.id)
        with self._patch_availability(sofa.product_variant_ids):
            self.assertEqual(
                sofa._get_ribbon(
                    auto_assign_ribbons=ribbon, variant=sofa.product_variant_id, for_template=True
                ),
                ribbon,
            )

    def test_out_of_stock_ribbon_describes_the_displayed_variant_on_the_product_page(self):
        """The product page shows one combination, so its ribbon keeps describing it,
        whatever the other variants are worth."""
        ribbon = self._out_of_stock_ribbon()
        sofa = self.sofa.with_context(website_id=self.website.id)
        with self._patch_availability(sofa.product_variant_id):
            self.assertEqual(
                sofa._get_ribbon(auto_assign_ribbons=ribbon, variant=sofa.product_variant_id),
                ribbon,
            )

    # === Product page CTA ===

    def _get_cta_classes(self):
        """Return the classes the product page is served with on its CTA wrapper."""
        page = self.url_open(self.sofa.website_url).text
        return re.search(r'id="o_wsale_cta_wrapper"\s+class="([^"]*)"', page).group(1)

    def test_sold_out_page_is_served_with_the_cta_already_hidden(self):
        """The landing combination is known server-side, so the page must not be served
        buyable and then corrected by the load-time round trip."""
        with self._patch_availability(self.sofa.product_variant_ids):
            self.assertIn("out_of_stock", self._get_cta_classes())

    def test_buyable_page_is_served_with_the_cta_shown(self):
        with self._patch_availability(self.env["product.product"]):
            self.assertNotIn("out_of_stock", self._get_cta_classes())

    # === Tour ===

    def test_sold_out_variant_muted_tour(self):
        """The sold-out neighbor value is struck through, follows selection,
        and survives no_variant option toggling."""
        with self._patch_availability(self.sold_out_variant):
            self.start_tour(self.sofa.website_url, "website_sale.variant_availability")

    def test_shop_click_lands_on_a_buyable_variant_tour(self):
        """Clicking a previewed value that isn't muted opens a variant that can be bought,
        not the sold-out one the default completion points at."""
        self.material_attribute.sudo().preview_variants = "visible"
        with self._patch_availability(self._get_variant("Wood", "White")):
            self.start_tour(
                "/shop?search=Test+Sofa", "website_sale.shop_variant_availability_landing"
            )

    def test_shop_tile_click_lands_on_a_buyable_variant_tour(self):
        """Opening the product from the tile pins no value, so the whole default moves onto
        a buyable variant, and the tile isn't ribboned while other variants sell."""
        self.env.ref("website_sale.out_of_stock_ribbon").sudo().assign = "out_of_stock"
        with self._patch_availability(self._get_variant("Wood", "White")):
            self.start_tour(
                "/shop?search=Test+Sofa", "website_sale.shop_variant_availability_tile_landing"
            )

    def test_unavailable_previewed_value_muted_on_shop_tour(self):
        """On /shop, a previewed value with nothing left to buy is muted, while a value
        with stock left isn't, and the muted one is still a link."""
        self.material_attribute.sudo().preview_variants = "visible"
        steel_variants = self._get_variant("Steel", "White") + self._get_variant("Steel", "Black")
        with self._patch_availability(steel_variants):
            self.start_tour("/shop?search=Test+Sofa", "website_sale.shop_variant_availability")
