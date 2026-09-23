from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from .common import BaseOrderTestCase


@tagged("post_install", "-at_install")
class TestHeaderMisc(BaseOrderTestCase):
    def test_has_archived_products(self):
        order = self._make_order()
        self._make_line(order=order)
        self.assertFalse(order.has_archived_products)

        self.product.active = False
        order.invalidate_recordset(["has_archived_products"])

        self.assertTrue(order.has_archived_products)

    def test_action_view_business_doc(self):
        order = self._make_order()

        action = order.action_view_business_doc()

        self.assertEqual(action["res_model"], "base.order.test")
        self.assertEqual(action["res_id"], order.id)

    def test_display_name_plain_without_context(self):
        order = self._make_order()

        self.assertEqual(order.display_name, order.name)

    def test_display_name_suffix_with_context(self):
        order = self._make_order()

        named = order.with_context(base_order_test_show_partner_name=True)

        self.assertIn(self.partner.name, named.display_name)

    def test_rec_names_search_toggles_partner(self):
        Model = self.env["base.order.test"]

        self.assertEqual(Model._rec_names_search, ["name"])
        self.assertIn(
            "partner_id.name",
            Model.with_context(
                base_order_test_show_partner_name=True
            )._rec_names_search,
        )

    def test_import_templates_shape(self):
        templates = self.env["base.order.test"].get_import_templates()

        self.assertTrue(templates)
        self.assertIn("label", templates[0])
        self.assertIn("template", templates[0])

    def test_is_late_search(self):
        now = fields.Datetime.now()
        late = self._make_order(date_commitment=now - timedelta(days=1))
        on_time = self._make_order(date_commitment=now + timedelta(days=1))
        undated = self._make_order()
        (late + on_time + undated).write({"state": "done"})
        draft_past = self._make_order(date_commitment=now - timedelta(days=1))

        Model = self.env["base.order.test"]
        made = late + on_time + undated + draft_past

        late_found = Model.search([("is_late", "=", True), ("id", "in", made.ids)])
        self.assertEqual(late_found, late)

        # The negation must also cover orders without a planned date.
        not_late = Model.search([("is_late", "=", False), ("id", "in", made.ids)])
        self.assertEqual(not_late, on_time + undated + draft_past)

    def test_is_late_search_rejects_bad_operator(self):
        with self.assertRaises(ValueError):
            self.env["base.order.test"].search([("is_late", ">", True)])

    def test_is_late_field_agrees_with_its_own_filter(self):
        """The field used to read False on a record its own filter matched."""
        now = fields.Datetime.now()
        late = self._make_order(date_commitment=now - timedelta(days=1))
        on_time = self._make_order(date_commitment=now + timedelta(days=1))
        (late + on_time).write({"state": "done"})
        draft_past = self._make_order(date_commitment=now - timedelta(days=1))

        self.assertTrue(late.is_late)
        self.assertFalse(on_time.is_late)
        self.assertFalse(draft_past.is_late, "a draft order is never late")

        found = self.env["base.order.test"].search(
            [("is_late", "=", True), ("id", "in", (late + on_time + draft_past).ids)],
        )
        self.assertEqual(found, late.filtered(lambda o: o.is_late))

    def test_is_late_is_false_on_an_unsaved_order(self):
        self.assertFalse(self.env["base.order.test"].new({}).is_late)

    def _confirmed_order_for(self, company, product):
        partner = self.env["res.partner"].create({"name": f"{company.name} partner"})
        order = (
            self.env["base.order.test"]
            .with_company(company)
            .create({"partner_id": partner.id, "company_id": company.id})
        )
        self.env["base.order.test.line"].create(
            {
                "order_id": order.id,
                "product_id": product.id,
                "product_qty": 1.0,
                "price_unit": 10.0,
                "name": "cmp",
            }
        )
        order.action_confirm()
        return order

    def test_show_comparison_is_true_when_another_order_carries_the_product(self):
        product = self.env["product.product"].create({"name": "Compared"})
        self._confirmed_order_for(self.env.company, product)

        draft = self._make_order()
        self._make_line(order=draft, product_id=product.id)

        self.assertTrue(draft.show_comparison)

    def test_show_comparison_ignores_orders_of_another_company(self):
        """A confirmed order elsewhere is not a comparison this order may draw on."""
        other_company = self.env["res.company"].create({"name": "Comparison Co"})
        self.env.user.company_ids = [(4, other_company.id)]
        product = self.env["product.product"].create({"name": "Cross-company"})
        self._confirmed_order_for(other_company, product)

        draft = self._make_order()
        self._make_line(order=draft, product_id=product.id)

        self.assertFalse(draft.show_comparison)

    def test_show_comparison_is_false_without_any_other_order(self):
        product = self.env["product.product"].create({"name": "Uncompared"})
        draft = self._make_order()
        self._make_line(order=draft, product_id=product.id)

        self.assertFalse(draft.show_comparison)
