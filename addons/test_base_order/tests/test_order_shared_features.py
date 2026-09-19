from unittest.mock import patch

from lxml import etree

from odoo.exceptions import AccessError
from odoo.fields import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOrderSharedFeatures(TransactionCase):
    _ALL_DOCUMENTS_GROUPS = {
        "sale.order": "sale.group_sale_salesman_all_leads",
        "purchase.order": "purchase.group_purchase_user_all",
    }
    _OWN_DOCUMENTS_GROUPS = {
        "sale.order": "sale.group_sale_salesman",
        "purchase.order": "purchase.group_purchase_user",
    }
    _MANAGER_GROUPS = {
        "sale.order": "sale.group_sale_manager",
        "purchase.order": "purchase.group_purchase_manager",
    }
    _PARTNER_RESPONSIBLE_FIELDS = {
        "sale.order": "user_id",
        "purchase.order": "user_purchase_id",
    }

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.report_config_id.external_report_layout_id = cls.env.ref(
            "web.external_layout_standard",
        )
        cls.partner = cls.env["res.partner"].create({"name": "Counterparty"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Shared Item",
                "list_price": 100.0,
                "standard_price": 60.0,
                "sale_ok": True,
                "purchase_ok": True,
            },
        )

    def _orders(self):
        return {
            "sale.order": self.env["sale.order"].create(
                {
                    "partner_id": self.partner.id,
                    "line_ids": [(0, 0, {"product_id": self.product.id})],
                },
            ),
            "purchase.order": self.env["purchase.order"].create(
                {
                    "partner_id": self.partner.id,
                    "line_ids": [(0, 0, {"product_id": self.product.id})],
                },
            ),
        }

    def test_is_in_order_is_true_for_the_order_in_context(self):
        for order in self._orders().values():
            with self.subTest(model=order._name):
                field = f"is_in_{order._get_order_type()}_order"
                product = self.product.with_context(order_id=order.id)
                product.invalidate_recordset([field])
                self.assertTrue(product[field])

    def test_is_in_order_is_false_without_an_order_in_context(self):
        for order in self._orders().values():
            with self.subTest(model=order._name):
                field = f"is_in_{order._get_order_type()}_order"
                self.product.invalidate_recordset([field])
                self.assertFalse(self.product[field])

    def test_search_is_in_order_finds_the_products_on_that_order(self):
        for order in self._orders().values():
            with self.subTest(model=order._name):
                field = f"is_in_{order._get_order_type()}_order"
                found = (
                    self.env["product.product"]
                    .with_context(order_id=order.id)
                    .search([(field, "in", [True])])
                )
                self.assertIn(self.product, found)

    def test_search_is_in_order_matches_nothing_without_an_order(self):
        self._orders()
        for order_type in ("sale", "purchase"):
            with self.subTest(order_type=order_type):
                self.assertFalse(
                    self.env["product.product"].search(
                        [(f"is_in_{order_type}_order", "in", [True])],
                    ),
                )

    def test_price_discounted_matches_the_stored_field(self):
        for order in self._orders().values():
            with self.subTest(model=order._name):
                line = order.line_ids[0]
                line.write({"price_unit": 200.0, "discount": 25.0})
                self.assertEqual(line._get_price_discounted(), 150.0)
                self.assertEqual(line.price_unit_discounted_taxexc, 150.0)

    def test_mark_as_sent_sets_the_flag_and_counts_the_send(self):
        for order in self._orders().values():
            with self.subTest(model=order._name):
                self.assertFalse(order.sent)
                self.assertEqual(order.count_sent, 0)
                order._mark_as_sent()
                self.assertTrue(order.sent)
                self.assertEqual(order.count_sent, 1)
                order._mark_as_sent()
                self.assertEqual(order.count_sent, 2)

    def _print_report_names(self, order):
        return [
            report_name
            for report_name, model_name in self.env["ir.actions.report"]
            ._get_order_print_report_map()
            .items()
            if model_name == order._name
        ]

    def test_rendering_a_print_report_flags_draft_orders_and_always_counts(self):
        for order in self._orders().values():
            with self.subTest(model=order._name):
                for count, report_name in enumerate(
                    self._print_report_names(order), start=1
                ):
                    self.env["ir.actions.report"]._render_qweb_pdf(
                        report_name, order.ids
                    )
                    self.assertTrue(order.printed_before)
                    self.assertEqual(order.count_print, count)

    def test_rendering_a_print_report_of_a_confirmed_order_counts_but_does_not_flag(
        self,
    ):
        for order in self._orders().values():
            with self.subTest(model=order._name):
                order.action_confirm()
                report_name = self._print_report_names(order)[0]
                self.env["ir.actions.report"]._render_qweb_pdf(report_name, order.ids)
                self.assertFalse(order.printed_before)
                self.assertEqual(order.count_print, 1)

    def test_every_order_type_counts_at_least_one_print_report(self):
        for order in self._orders().values():
            with self.subTest(model=order._name):
                self.assertTrue(self._print_report_names(order))

    def test_rendering_an_unrelated_report_of_the_order_model_does_not_count(self):
        order = self._orders()["sale.order"]
        self.env["ir.actions.report"]._render_qweb_pdf(
            "sale.action_report_pro_forma_invoice", order.ids
        )
        self.assertEqual(order.count_print, 0)

    def test_send_by_email_opens_the_composer_with_the_template(self):
        for order in self._orders().values():
            with self.subTest(model=order._name):
                action = order._action_send_by_email()
                ctx = action["context"]
                self.assertEqual(action["res_model"], "mail.compose.message")
                self.assertEqual(ctx["default_model"], order._name)
                self.assertEqual(ctx["default_res_ids"], order.ids)
                self.assertEqual(ctx["default_composition_mode"], "comment")
                self.assertTrue(ctx["force_email"])
                self.assertEqual(
                    ctx["default_template_id"],
                    order._get_mail_template().id,
                )
                self.assertTrue(ctx[order._get_mark_sent_context_key()])

    def test_send_by_email_switches_to_mass_mail_for_several_orders(self):
        orders = self.env["sale.order"].create(
            [
                {
                    "partner_id": self.partner.id,
                    "line_ids": [(0, 0, {"product_id": self.product.id})],
                },
            ]
            * 2,
        )
        ctx = orders._action_send_by_email()["context"]
        self.assertEqual(ctx["default_composition_mode"], "mass_mail")
        self.assertNotIn("force_email", ctx)
        self.assertNotIn("default_template_id", ctx)
        self.assertNotIn(orders._get_mark_sent_context_key(), ctx)

    def test_send_by_email_opens_in_the_template_language(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        for order in self._orders().values():
            with self.subTest(model=order._name):
                template = order._get_mail_template()
                template.lang = "fr_FR"
                ctx = order._action_send_by_email()["context"]
                self.assertEqual(ctx["lang"], "fr_FR")

    def test_send_by_email_keeps_the_user_language_without_a_template_lang(self):
        for order in self._orders().values():
            with self.subTest(model=order._name):
                order._get_mail_template().lang = False
                ctx = order.with_context(lang="en_US")._action_send_by_email()[
                    "context"
                ]
                self.assertEqual(ctx["lang"], "en_US")

    VALIDITY_SETTINGS = (
        ("quotation_validity_days", "_onchange_quotation_validity_days"),
        ("po_quotation_validity_days", "_onchange_po_quotation_validity_days"),
    )
    LOCK_SETTINGS = (
        ("lock_confirmed_so", "order_lock_so"),
        ("lock_confirmed_po", "order_lock_po"),
    )

    def test_negative_validity_days_is_reset_to_the_default_with_a_warning(self):
        for field, onchange in self.VALIDITY_SETTINGS:
            with self.subTest(field=field):
                settings = self.env["res.config.settings"].new({field: -5})

                result = getattr(settings, onchange)()

                self.assertIn("warning", result)
                self.assertEqual(
                    settings[field],
                    self.env["res.company"].default_get([field])[field],
                )

    def test_non_negative_validity_days_is_left_alone(self):
        for field, onchange in self.VALIDITY_SETTINGS:
            with self.subTest(field=field):
                settings = self.env["res.config.settings"].new({field: 7})

                self.assertIsNone(getattr(settings, onchange)())
                self.assertEqual(settings[field], 7)

    def test_zero_validity_days_is_accepted(self):
        for field, onchange in self.VALIDITY_SETTINGS:
            with self.subTest(field=field):
                settings = self.env["res.config.settings"].new({field: 0})

                self.assertIsNone(getattr(settings, onchange)())
                self.assertEqual(settings[field], 0)

    def test_lock_checkbox_reaches_the_company_setting(self):
        for checkbox, lock_field in self.LOCK_SETTINGS:
            with self.subTest(checkbox=checkbox):
                settings = self.env["res.config.settings"].create({checkbox: True})

                settings._sync_order_lock(checkbox, lock_field)

                self.assertEqual(settings[lock_field], "lock")
                self.assertEqual(self.env.company[lock_field], "lock")

    def test_clearing_the_lock_checkbox_reaches_the_company_setting(self):
        for checkbox, lock_field in self.LOCK_SETTINGS:
            with self.subTest(checkbox=checkbox):
                self.env.company[lock_field] = "lock"
                settings = self.env["res.config.settings"].create({checkbox: False})

                settings._sync_order_lock(checkbox, lock_field)

                self.assertEqual(self.env.company[lock_field], "edit")

    def _invoice_lines_of(self, order):
        order.action_confirm()
        invoice = order._create_invoices()
        return invoice.invoice_line_ids.filtered("product_id")

    def test_both_order_types_register_their_invoice_line_link(self):
        link_fields = self.env["account.move.line"]._get_fields_order_line_link()

        self.assertIn("sale_line_ids", link_fields)
        self.assertIn("purchase_line_ids", link_fields)

    def test_invoice_line_links_back_to_its_order_line(self):
        for order in self._orders().values():
            with self.subTest(model=order._name):
                field = f"{order._get_order_type()}_line_ids"

                invoice_lines = self._invoice_lines_of(order)

                self.assertTrue(invoice_lines)
                self.assertEqual(invoice_lines[field], order.line_ids)

    def test_copying_an_invoice_line_keeps_the_order_line_link(self):
        for order in self._orders().values():
            with self.subTest(model=order._name):
                field = f"{order._get_order_type()}_line_ids"
                invoice_line = self._invoice_lines_of(order)[:1]

                values = {}
                invoice_line._copy_data_extend_business_fields(values)

                self.assertEqual(values[field][0][2], order.line_ids.ids)

    def test_invoice_line_inherits_the_order_lines_analytic_distribution(self):
        plan = self.env["account.analytic.plan"].create({"name": "Shared Plan"})
        account = self.env["account.analytic.account"].create(
            {"name": "Shared Account", "plan_id": plan.id},
        )
        distribution = {str(account.id): 100.0}
        for order in self._orders().values():
            with self.subTest(model=order._name):
                order.line_ids.analytic_distribution = distribution
                invoice_line = self._invoice_lines_of(order)[:1]

                self.assertEqual(
                    invoice_line._related_analytic_distribution(),
                    distribution,
                )

    def test_a_salesman_without_purchase_rights_invoices_an_order(self):
        salesman = self.env["res.users"].create(
            {
                "name": "Salesman without purchase",
                "login": "shared_features_salesman",
                "group_ids": [
                    Command.set([self.env.ref("sale.group_sale_salesman").id])
                ],
            },
        )
        self.assertFalse(
            self.env["purchase.order.line"].with_user(salesman).has_access("read")
        )
        order = self._orders()["sale.order"]
        order.user_id = salesman
        order.action_confirm()

        invoice = order._create_invoices()
        invoice_line = invoice.invoice_line_ids.filtered("product_id")[:1].with_user(
            salesman
        )
        values = {}
        invoice_line._copy_data_extend_business_fields(values)

        self.assertEqual(invoice_line._related_analytic_distribution(), {})
        self.assertEqual(values["sale_line_ids"][0][2], order.line_ids.ids)
        self.assertEqual(values["purchase_line_ids"][0][2], [])

    def _form_reader(self, group_xmlid):
        return self.env["res.users"].create(
            {
                "name": f"Reader of {group_xmlid}",
                "login": f"form_reader_{group_xmlid}",
                "group_ids": [Command.set([self.env.ref(group_xmlid).id])],
            },
        )

    def _read_the_invoice_form_as(self, user, move):
        Move = self.env["account.move"].with_user(user)
        views = Move.get_views([(False, "form")])
        arch = etree.fromstring(views["views"]["form"]["arch"])
        for node in arch.xpath("//field[not(ancestor::field)]"):
            with self.subTest(user=user.login, field=node.get("name")):
                Move.browse(move.id).invalidate_recordset()
                Move.browse(move.id).web_read({node.get("name"): {}})

    def test_an_invoice_form_opens_for_each_side_without_the_other_sides_rights(self):
        salesman = self._form_reader("sale.group_sale_salesman")
        buyer = self._form_reader("purchase.group_purchase_user")
        orders = self._orders()
        for order in orders.values():
            order.action_confirm()
        invoice = orders["sale.order"]._create_invoices()
        invoice.invoice_user_id = salesman
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner.id,
                "invoice_user_id": buyer.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "purchase_line_ids": [
                                Command.set(orders["purchase.order"].line_ids.ids)
                            ],
                        }
                    )
                ],
            },
        )
        self.assertTrue(invoice.with_user(salesman).has_access("read"))
        self.assertTrue(bill.with_user(buyer).has_access("read"))
        self._read_the_invoice_form_as(salesman, invoice)
        self._read_the_invoice_form_as(buyer, bill)

    def test_invoice_line_carries_the_products_warning(self):
        for order_type, group in (
            ("sale", "sale.group_warning_sale"),
            ("purchase", "purchase.group_warning_purchase"),
        ):
            with self.subTest(order_type=order_type):
                field = f"{order_type}_line_warn_msg"
                self.product[field] = "Handle with care"
                self.env.user.group_ids += self.env.ref(group)

                invoice_line = self.env["account.move.line"].new(
                    {"product_id": self.product.id},
                )

                self.assertEqual(invoice_line[field], "Handle with care")

    def test_invoice_line_hides_the_warning_without_the_group(self):
        for order_type, group in (
            ("sale", "sale.group_warning_sale"),
            ("purchase", "purchase.group_warning_purchase"),
        ):
            with self.subTest(order_type=order_type):
                field = f"{order_type}_line_warn_msg"
                self.product[field] = "Handle with care"
                self.env.user.group_ids -= self.env.ref(group)

                invoice_line = self.env["account.move.line"].new(
                    {"product_id": self.product.id},
                )

                self.assertEqual(invoice_line[field], "")

    def _user_in_group(self, group_xmlid, suffix=""):
        return self.env["res.users"].create(
            {
                "name": "Order Responsible",
                "login": f"order-responsible-{group_xmlid}{suffix}",
                "group_ids": [Command.set(self.env.ref(group_xmlid).ids)],
            },
        )

    def _order_of(self, model, group_xmlid):
        user = self._user_in_group(group_xmlid)
        order = self.env[model].with_user(user).create({"partner_id": self.partner.id})
        return user, order

    def test_each_order_type_declares_a_group_that_resolves(self):
        for model, group in self._ALL_DOCUMENTS_GROUPS.items():
            with self.subTest(model=model):
                self.assertEqual(self.env[model]._get_all_documents_group(), group)
                self.assertTrue(self.env.ref(group, raise_if_not_found=False))

    def test_a_restricted_user_cannot_hand_an_order_to_someone_else(self):
        for model, group in self._OWN_DOCUMENTS_GROUPS.items():
            with self.subTest(model=model):
                user, order = self._order_of(model, group)
                other = self._user_in_group(self._ALL_DOCUMENTS_GROUPS[model])

                with self.assertRaises(AccessError):
                    order.write({"user_id": other.id})

                self.assertEqual(order.sudo().user_id, user)

    def test_a_restricted_user_may_still_make_themselves_responsible(self):
        for model, group in self._OWN_DOCUMENTS_GROUPS.items():
            with self.subTest(model=model):
                user, order = self._order_of(model, group)
                order.sudo().user_id = False

                order.write({"user_id": user.id})

                self.assertEqual(order.user_id, user)

    def test_access_to_all_documents_may_reassign_the_responsible(self):
        for model, group in self._ALL_DOCUMENTS_GROUPS.items():
            with self.subTest(model=model):
                _user, order = self._order_of(model, group)
                other = self._user_in_group(self._MANAGER_GROUPS[model])

                order.write({"user_id": other.id})

                self.assertEqual(order.user_id, other)

    def test_a_manager_may_reassign_the_responsible(self):
        for model, group in self._MANAGER_GROUPS.items():
            with self.subTest(model=model):
                _user, order = self._order_of(model, group)
                other = self._user_in_group(self._ALL_DOCUMENTS_GROUPS[model])

                order.write({"user_id": other.id})

                self.assertEqual(order.user_id, other)

    def test_the_guard_stands_aside_for_a_model_declaring_no_group(self):
        for model, group in self._OWN_DOCUMENTS_GROUPS.items():
            with self.subTest(model=model):
                _user, order = self._order_of(model, group)
                other = self._user_in_group(self._ALL_DOCUMENTS_GROUPS[model])

                with self.assertRaises(AccessError):
                    order._check_write_user_id({"user_id": other.id})

                with patch.object(
                    type(self.env[model]),
                    "_get_all_documents_group",
                    lambda self: False,
                ):
                    order._check_write_user_id({"user_id": other.id})

    def test_the_guard_does_not_fire_when_the_partner_recomputes_the_responsible(self):
        for model, group in self._OWN_DOCUMENTS_GROUPS.items():
            with self.subTest(model=model):
                user, order = self._order_of(model, group)
                assignee = self._user_in_group(self._ALL_DOCUMENTS_GROUPS[model])
                partner = self.env["res.partner"].create(
                    {
                        "name": "Assigned Counterparty",
                        self._PARTNER_RESPONSIBLE_FIELDS[model]: assignee.id,
                    },
                )

                order.write({"partner_id": partner.id})

                self.assertEqual(order.sudo().user_id, user, "the compute left it be")

    def test_sudo_bypasses_the_guard(self):
        for model, group in self._OWN_DOCUMENTS_GROUPS.items():
            with self.subTest(model=model):
                _user, order = self._order_of(model, group)
                other = self._user_in_group(self._ALL_DOCUMENTS_GROUPS[model])

                order.sudo().write({"user_id": other.id})

                self.assertEqual(order.sudo().user_id, other)

    _COUNT_FIELDS = {
        "sale.order": "sale_order_count",
        "purchase.order": "purchase_order_count",
    }

    def test_order_count_is_not_narrowed_by_the_personal_rule(self):
        """`_compute_order_count` must see every order for the partner, like
        `_compute_recent_orders_count` already does, not just the ones the
        acting salesperson personally owns."""
        for model, group in self._OWN_DOCUMENTS_GROUPS.items():
            with self.subTest(model=model):
                count_field = self._COUNT_FIELDS[model]
                user_a = self._user_in_group(group, suffix="-a")
                user_b = self._user_in_group(group, suffix="-b")
                self.env[model].with_user(user_a).create(
                    {"partner_id": self.partner.id, "user_id": user_a.id},
                )
                self.env[model].with_user(user_b).create(
                    {"partner_id": self.partner.id, "user_id": user_b.id},
                )

                count = self.partner.with_user(user_a)[count_field]

                self.assertEqual(
                    count,
                    2,
                    "the personal-orders record rule must not narrow the "
                    "stat-button count the way it narrows the order list",
                )
