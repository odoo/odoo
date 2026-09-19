import inspect
from datetime import timedelta
from unittest.mock import patch

from freezegun import freeze_time

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command
from odoo.tests import Form, HttpCase, tagged
from odoo.tools.safe_eval import safe_eval

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.sale.tests.common import SaleCommon


@tagged("post_install", "-at_install")
class TestSaleOrder(SaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner1, cls.partner2 = cls.env["res.partner"].create(
            [
                {"name": "Partner 1"},
                {"name": "Partner 2"},
            ]
        )
        cls.confirmation_email_template = cls.sale_order._get_confirmation_template()
        cls.async_emails_cron = cls.env.ref("sale.send_pending_emails_cron")

    def test_line_name_computes_before_the_order_exists(self):
        line = self.env["sale.order.line"].new({"product_id": self.product.id})
        self.assertFalse(line.order_id)
        self.assertEqual(line.order_id._get_lang(), self.env.lang)
        self.assertTrue(line.name)

    def test_form_opens_with_a_default_line_and_no_order(self):
        with Form(self.env["sale.order"]) as order_form:
            order_form.partner_id = self.partner
            with order_form.line_ids.new() as line:
                line.product_id = self.product
        self.assertTrue(order_form.record.line_ids.name)

    def test_computes_auto_fill(self):
        free_product, dummy_product = self.env["product.product"].create(
            [
                {
                    "name": "Free product",
                    "list_price": 0.0,
                },
                {
                    "name": "Dummy product",
                    "list_price": 0.0,
                },
            ]
        )
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "line_ids": [
                    Command.create(
                        {
                            "display_type": "line_section",
                            "name": "Dummy section",
                        }
                    ),
                    Command.create(
                        {
                            "display_type": "line_section",
                            "name": "Dummy section",
                        }
                    ),
                    Command.create(
                        {
                            "product_id": free_product.id,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": dummy_product.id,
                        }
                    ),
                ],
            }
        )

        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
            }
        )
        self.env["sale.order.line"].create(
            [
                {
                    "display_type": "line_section",
                    "name": "Dummy section",
                    "order_id": order.id,
                },
                {
                    "display_type": "line_section",
                    "name": "Dummy section",
                    "order_id": order.id,
                },
                {
                    "product_id": free_product.id,
                    "order_id": order.id,
                },
                {
                    "product_id": dummy_product.id,
                    "order_id": order.id,
                },
            ]
        )

    def test_sale_order_standard_flow(self):
        self.assertEqual(
            self.sale_order.amount_total, 725.0, "Sale: total amount is wrong"
        )
        self.sale_order.line_ids._compute_product_readonly()
        self.assertFalse(self.sale_order.line_ids[0].product_readonly)

        email_act = self.sale_order.action_send_quotation()
        email_ctx = email_act.get("context", {})
        self.sale_order.with_context(**email_ctx).message_post_with_source(
            self.env["mail.template"].browse(email_ctx.get("default_template_id")),
            subtype_xmlid="mail.mt_comment",
        )
        self.assertTrue(self.sale_order.sent, "Sale: sent flag after sending is wrong")
        self.sale_order.line_ids._compute_product_readonly()
        self.assertFalse(self.sale_order.line_ids[0].product_readonly)

        self.sale_order.action_confirm()
        self.assertTrue(self.sale_order.state == "done")
        self.assertTrue(self.sale_order.invoice_state == "to do")

    def test_sale_order_send_to_self(self):
        sale_order = (
            self.env["sale.order"]
            .with_user(self.sale_user)
            .create(
                {
                    "partner_id": self.sale_user.partner_id.id,
                }
            )
        )
        email_ctx = sale_order.action_send_quotation().get("context", {})
        mail_template = (
            self.env["mail.template"]
            .browse(email_ctx.get("default_template_id"))
            .copy({"auto_delete": False})
        )
        sale_order.with_context(**email_ctx).with_user(
            self.sale_user
        ).message_post_with_source(
            mail_template,
            subtype_xmlid="mail.mt_comment",
        )
        self.assertTrue(
            sale_order.sent, "Sale : sent flag should be True after sending"
        )
        mail_message = sale_order.message_ids[0]
        self.assertEqual(
            mail_message.author_id,
            sale_order.partner_id,
            "Sale: author should be same as customer",
        )
        self.assertEqual(
            mail_message.author_id,
            mail_message.partner_ids,
            'Sale: author should be in composer recipients thanks to "partner_to" field set on template',
        )
        self.assertEqual(
            mail_message.partner_ids,
            mail_message.sudo().mail_ids.recipient_ids,
            "Sale: author should receive mail due to presence in composer recipients",
        )

    def test_sale_sequence(self):
        self.env["ir.sequence"].search(
            [
                ("code", "=", "sale.order"),
            ]
        ).write(
            {
                "use_date_range": True,
                "prefix": "SO/%(range_year)s/",
            }
        )
        sale_order = self.sale_order.copy({"date_order": "2019-01-01"})
        self.assertTrue(sale_order.name.startswith("SO/2019/"))
        sale_order = self.sale_order.copy({"date_order": "2020-01-01"})
        self.assertTrue(sale_order.name.startswith("SO/2020/"))
        sale_order = self.sale_order.with_context(tz="Europe/Brussels").copy(
            {"date_order": "2019-12-31 23:30:00"}
        )
        self.assertTrue(sale_order.name.startswith("SO/2020/"))

    def test_unlink_cancel(self):
        so_copy = self.sale_order.copy()
        with self.assertRaises(AccessError):
            so_copy.with_user(self.sale_user).unlink()
        self.assertTrue(
            so_copy.unlink(), "Sale: deleting a quotation should be possible"
        )

        so_copy = self.sale_order.copy()
        so_copy.action_confirm()
        self.assertTrue(so_copy.state == "done", 'Sale: SO should be in state "done"')
        so_copy._action_cancel()
        self.assertTrue(
            so_copy.state == "cancel", 'Sale: SO should be in state "cancel"'
        )
        with self.assertRaises(AccessError):
            so_copy.with_user(self.sale_user).unlink()
        self.assertTrue(
            so_copy.unlink(), "Sale: deleting a cancelled SO should be possible"
        )

        self.sale_order.action_confirm()
        self.assertTrue(
            self.sale_order.state == "done", 'Sale: SO should be in state "done"'
        )
        with self.assertRaises(UserError):
            self.sale_order.unlink()

        self.sale_order.action_lock()
        self.assertTrue(self.sale_order.state == "done")
        self.assertTrue(self.sale_order.locked)
        with self.assertRaises(UserError):
            self.sale_order.unlink()

    def _create_sale_order(self):
        return (
            self.env["sale.order"]
            .with_context(default_sale_order_template_id=False)
            .create(
                {
                    "partner_id": self.partner.id,
                }
            )
        )

    def test_invoicing_terms(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "account.use_invoice_terms", True
        )

        self.env.company.account_config_id.terms_type = "plain"
        self.env.company.account_config_id.invoice_terms = "Coin coin"
        sale_order = self._create_sale_order()
        self.assertEqual(sale_order.notes, "<p>Coin coin</p>")

        self.env.company.account_config_id.terms_type = "html"
        sale_order = self._create_sale_order()
        self.assertIn("Terms &amp; Conditions: ", sale_order.notes)

    def test_validity_days(self):
        self.env.company.quotation_validity_days = 5
        with freeze_time("2020-05-02"):
            sale_order = self._create_sale_order()

            self.assertEqual(
                sale_order.date_validity, fields.Date.today() + timedelta(days=5)
            )
        self.env.company.quotation_validity_days = 0
        sale_order = self._create_sale_order()
        self.assertFalse(
            sale_order.date_validity,
            "No validity date must be specified if the company validity duration is 0",
        )

    def test_so_names(self):
        SaleOrder = self.env["sale.order"].with_context(sale_show_partner_name=True)

        res = SaleOrder.name_search(name=self.sale_order.partner_id.name)
        self.assertEqual(res[0][0], self.sale_order.id)

        self.assertNotIn(self.sale_order.partner_id.name, self.sale_order.display_name)
        self.assertIn(
            self.sale_order.partner_id.name,
            self.sale_order.with_context(sale_show_partner_name=True).display_name,
        )

    def test_sol_names(self):
        no_variant_attr = self.env["product.attribute"].create(
            {
                "name": "Attribute",
                "create_variant": "no_variant",
                "value_ids": [
                    Command.create({"name": "Value 1", "sequence": 1}),
                    Command.create({"name": "Value 2", "sequence": 2}),
                ],
            }
        )
        no_variant_product_tmpl = self.env["product.template"].create(
            {
                "name": "No Variant",
                "attribute_line_ids": [
                    Command.create(
                        {
                            "attribute_id": no_variant_attr.id,
                            "value_ids": no_variant_attr.value_ids.ids,
                        }
                    )
                ],
            }
        )
        no_variant_product = no_variant_product_tmpl.product_variant_id
        ptals = no_variant_product_tmpl.valid_product_template_attribute_line_ids
        ptav1 = next(iter(ptals.product_template_value_ids))
        product_with_desc = self.env["product.product"].create(
            {
                "name": "Product with description",
                "description_sale": "Additional\ninfo.",
            }
        )

        self.sale_order.line_ids = [
            Command.create({"is_downpayment": True}),
            Command.create({"display_type": "line_note", "name": "Foo\nBar\nBaz"}),
            Command.create(
                {
                    "product_id": no_variant_product.id,
                    "product_no_variant_attribute_value_ids": ptav1.ids,
                }
            ),
            Command.create({"product_id": product_with_desc.id}),
        ]
        sol1, sol2, sol3, sol4, sol5, sol6 = self.sale_order.line_ids
        sol1.name += "\nOK THANK YOU\nGOOD BYE"

        self.assertEqual(
            sol1.display_name,
            f"{self.sale_order.name} - OK THANK YOU ({self.partner.name})",
            "Product line with a custom description should display the first line of description",
        )
        self.assertEqual(
            sol2.display_name,
            f"{self.sale_order.name} - {sol2.product_id.display_name} ({self.partner.name})",
            "Product line without description should display the product name",
        )
        self.assertEqual(
            sol3.display_name,
            f"{self.sale_order.name} - {sol3.name} ({self.partner.name})",
            "Down payment line should display the down payment name",
        )
        self.assertEqual(
            sol4.display_name,
            f"{self.sale_order.name} - Foo ({self.partner.name})",
            "Multi-line note should display the first line only",
        )
        self.assertIn(f"{no_variant_attr.name}: {ptav1.name}", sol5.name.split("\n"))
        self.assertEqual(
            sol5.display_name,
            f"{self.sale_order.name} - {no_variant_product.name} ({self.partner.name})",
            "Lines with attribute-based descriptions should display the product name",
        )
        self.assertEqual(
            sol6.display_name,
            f"{self.sale_order.name} - {product_with_desc.display_name} ({self.partner.name})",
            "Product lines with standard sales description should display the product name",
        )

    def test_state_changes(self):
        self.sale_order.action_quotation_sent()

        self.assertTrue(self.sale_order.sent)
        self.assertNotIn(
            self.sale_order.partner_id,
            self.sale_order.message_partner_ids,
            "Customer should not be added automatically in followers",
        )

        self.env.user.group_ids += self.env.ref("sale.group_auto_done_setting")
        self.sale_order.action_confirm()
        self.assertEqual(self.sale_order.state, "done")
        self.assertTrue(self.sale_order.locked)
        with self.assertRaises(UserError):
            self.sale_order.action_confirm()

        self.sale_order.action_unlock()
        self.assertEqual(self.sale_order.state, "done")

    def test_sol_name_search(self):
        self.env["sale.order"]._search([("line_ids", "ilike", "product")])

        name_search_data = self.env["sale.order.line"].name_search(
            name=self.sale_order.name
        )
        sol_ids_found = dict(name_search_data).keys()
        self.assertEqual(list(sol_ids_found), self.sale_order.line_ids.ids)

    def test_zero_quantity(self):
        order_line = self.sale_order.line_ids[0]
        order_line.product_qty = 0.0
        order_line.product_uom_id = self.uom_dozen
        self.assertEqual(order_line.product_qty, 0.0)
        self.assertEqual(order_line.product_uom_qty, 0.0)

    def test_discount_rounding(self):
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_qty": 1,
                            "price_unit": 192,
                            "discount": 74.246,
                        },
                    )
                ],
            }
        )
        self.assertEqual(
            sale_order.line_ids.price_subtotal,
            49.44,
            "Subtotal should be equal to 192 * (1 - 0.7425)",
        )
        self.assertEqual(sale_order.line_ids.discount, 74.25)

    def test_tax_amount_rounding(self):
        tax_a = self.env["account.tax"].create(
            {
                "name": "Test tax",
                "type_tax_use": "sale",
                "price_include_override": "tax_excluded",
                "amount_type": "percent",
                "amount": 15.0,
            }
        )

        self.env.company.account_config_id.tax_calculation_rounding_method = (
            "round_per_line"
        )
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_qty": 1,
                            "price_unit": 6.7,
                            "discount": 0,
                            "tax_ids": tax_a.ids,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_qty": 1,
                            "price_unit": 6.7,
                            "discount": 0,
                            "tax_ids": tax_a.ids,
                        }
                    ),
                ],
            }
        )
        self.assertEqual(sale_order.amount_total, 15.42, "")

        self.env.company.account_config_id.tax_calculation_rounding_method = (
            "round_globally"
        )
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_qty": 1,
                            "price_unit": 6.7,
                            "discount": 0,
                            "tax_ids": tax_a.ids,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_qty": 1,
                            "price_unit": 6.7,
                            "discount": 0,
                            "tax_ids": tax_a.ids,
                        }
                    ),
                ],
            }
        )
        self.assertEqual(sale_order.amount_total, 15.41, "")

    def test_order_auto_lock_with_public_user(self):
        public_user = self.env.ref("base.public_user")
        self.sale_order.create_uid.group_ids += self.env.ref(
            "sale.group_auto_done_setting"
        )
        self.sale_order.with_user(public_user.id).sudo().action_confirm()

        self.assertFalse(public_user.has_group("sale.group_auto_done_setting"))
        self.assertTrue(self.sale_order.locked)

    def test_order_status_email_is_sent_synchronously_if_not_configured(self):
        self.env["ir.config_parameter"].set_param("sale.async_emails", "False")

        self.sale_order._send_mail_order_notification(self.confirmation_email_template)
        self.assertFalse(
            self.env["ir.cron.trigger"].search_count(
                [("cron_id", "=", self.async_emails_cron.id)]
            ),
            msg="The email should be sent synchronously when the system parameter is not set.",
        )

    def test_order_status_email_is_sent_asynchronously_if_configured(self):
        self.env["ir.config_parameter"].set_param("sale.async_emails", "True")

        self.sale_order._send_mail_order_notification(self.confirmation_email_template)
        self.assertTrue(
            self.sale_order.pending_email_template_id,
            msg="The email template should be saved on the sales order.",
        )
        self.assertTrue(
            self.env["ir.cron.trigger"].search_count(
                [("cron_id", "=", self.async_emails_cron.id)]
            ),
            msg="The asynchronous email sending cron should be triggered.",
        )

    def test_async_emails_cron_does_not_trigger_itself(self):
        self.env["ir.config_parameter"].set_param("sale.async_emails", "True")
        self.sale_order.pending_email_template_id = self.confirmation_email_template

        with self.enter_registry_test_mode():
            self.env.ref("sale.send_pending_emails_cron").method_direct_trigger()
        self.assertFalse(
            self.sale_order.pending_email_template_id,
            msg="The email template should be removed from the sales order.",
        )
        self.assertFalse(
            self.env["ir.cron.trigger"].search_count(
                [("cron_id", "=", self.async_emails_cron.id)]
            ),
            msg="The email should be sent synchronously when requested by the cron.",
        )

    def test_scheduled_mark_so_as_sent(self):
        order = self.sale_order
        composer = (
            self.env["mail.compose.message"]
            .with_context(
                active_id=order.id,
                active_ids=order.ids,
                active_model=order._name,
                mark_so_as_sent=True,
            )
            .new(
                {
                    "body": "<h1>Your Sales Order</h1>",
                    "scheduled_date": fields.Datetime.now() + timedelta(days=1),
                }
            )
        )
        composer.action_schedule_message()

        scheduled_message = self.env["mail.scheduled.message"].search(
            [
                ("model", "=", order._name),
                ("res_id", "=", order.id),
            ],
            limit=1,
        )
        self.assertEqual(order.state, "draft")
        scheduled_message.post_message()
        self.assertTrue(order.sent)

    def test_so_discount_is_not_reset(self):
        with patch(
            "odoo.addons.sale.models.sale_order_line.SaleOrderLine"
            "._compute_price_and_discount"
        ) as patched:
            self.sale_order.action_confirm()
            self.sale_order.line_ids.flush_recordset(["discount"])
            patched.assert_not_called()

    def test_so_company_empty(self):
        company_2 = self.env["res.company"].create({"name": "Company 2"})
        self.env = self.env(
            context=dict(
                self.env.context,
                allowed_company_ids=[self.env.company.id, company_2.id],
            )
        )
        so_form = Form(self.env["sale.order"])
        with self.assertRaises(ValidationError):
            so_form.company_id = self.env["res.company"]

    def test_so_is_not_invoiceable_if_only_discount_line_is_to_invoice(self):
        self.sale_order.line_ids.product_id.invoice_policy = "transferred"
        self.sale_order.action_confirm()

        self.assertEqual(
            self.sale_order.invoice_state,
            "to do",
            "the lines are 'no' only because nothing has been delivered yet, "
            "which is a quantity still owed rather than one that will never come",
        )
        standard_lines = self.sale_order.line_ids

        self.env["sale.order.discount"].create(
            {
                "sale_order_id": self.sale_order.id,
                "discount_amount": 33,
                "discount_type": "amount",
            }
        ).action_apply_discount()

        discount_line = self.sale_order.line_ids - standard_lines
        self.assertEqual(discount_line.invoice_state, "to do")
        self.assertEqual(self.sale_order.invoice_state, "no")

    def test_so_is_invoiceable_if_only_discount_line_remains_to_invoice(self):
        self.sale_order.line_ids.product_id.invoice_policy = "transferred"
        self.sale_order.action_confirm()

        self.assertEqual(
            self.sale_order.invoice_state,
            "to do",
            "the lines are 'no' only because nothing has been delivered yet, "
            "which is a quantity still owed rather than one that will never come",
        )
        standard_lines = self.sale_order.line_ids

        for sol in standard_lines:
            sol.qty_transferred = sol.product_uom_qty
        invoice = self.sale_order._create_invoices()
        invoice.action_post()

        self.assertEqual(self.sale_order.invoice_state, "done")

        self.env["sale.order.discount"].create(
            {
                "sale_order_id": self.sale_order.id,
                "discount_amount": 33,
                "discount_type": "amount",
            }
        ).action_apply_discount()

        discount_line = self.sale_order.line_ids - standard_lines
        self.assertEqual(discount_line.invoice_state, "to do")
        self.assertEqual(
            self.sale_order.invoice_state,
            "partial",
            "the standard lines are billed and the discount line is not, "
            "which is partial progress rather than untouched work",
        )

    def test_so_with_fixed_discount_zero_amount(self):
        initial_total = self.sale_order.amount_total
        self.env["sale.order.discount"].create(
            {
                "sale_order_id": self.sale_order.id,
                "discount_amount": 0.0,
                "discount_type": "amount",
            }
        ).action_apply_discount()
        self.assertEqual(self.sale_order.amount_total, initial_total)

    def test_sale_order_line_product_taxes_on_branch(self):
        company = self.env.company
        branch_x = self.env["res.company"].create(
            {
                "name": "Branch X",
                "country_id": company.country_id.id,
                "parent_id": company.id,
            }
        )
        branch_xx = self.env["res.company"].create(
            {
                "name": "Branch XX",
                "country_id": company.country_id.id,
                "parent_id": branch_x.id,
            }
        )
        tax_groups = self.env["account.tax.group"].create(
            [
                {
                    "name": "Tax Group",
                    "company_ids": [Command.set(company.ids)],
                },
                {
                    "name": "Tax Group X",
                    "company_ids": [Command.set(branch_x.ids)],
                },
                {
                    "name": "Tax Group XX",
                    "company_ids": [Command.set(branch_xx.ids)],
                },
            ]
        )
        tax_a = self.env["account.tax"].create(
            {
                "name": "Tax A",
                "type_tax_use": "sale",
                "amount_type": "percent",
                "amount": 10,
                "tax_group_id": tax_groups[0].id,
                "company_ids": [Command.set(company.ids)],
            }
        )
        tax_b = self.env["account.tax"].create(
            {
                "name": "Tax B",
                "type_tax_use": "sale",
                "amount_type": "percent",
                "amount": 15,
                "tax_group_id": tax_groups[0].id,
                "company_ids": [Command.set(company.ids)],
            }
        )
        tax_x = self.env["account.tax"].create(
            {
                "name": "Tax X",
                "type_tax_use": "sale",
                "amount_type": "percent",
                "amount": 20,
                "tax_group_id": tax_groups[1].id,
                "company_ids": [Command.set(branch_x.ids)],
            }
        )
        tax_xx = self.env["account.tax"].create(
            {
                "name": "Tax XX",
                "type_tax_use": "sale",
                "amount_type": "percent",
                "amount": 25,
                "tax_group_id": tax_groups[2].id,
                "company_ids": [Command.set(branch_xx.ids)],
            }
        )
        product_all_taxes = self.env["product.product"].create(
            {
                "name": "Product all taxes",
                "taxes_id": [Command.set((tax_a + tax_b + tax_x + tax_xx).ids)],
            }
        )
        product_no_xx_tax = self.env["product.product"].create(
            {
                "name": "Product no tax from XX",
                "taxes_id": [Command.set((tax_a + tax_b + tax_x).ids)],
            }
        )
        product_no_branch_tax = self.env["product.product"].create(
            {
                "name": "Product no tax from branch",
                "taxes_id": [Command.set((tax_a + tax_b).ids)],
            }
        )
        product_no_tax = self.env["product.product"].create(
            {
                "name": "Product no tax",
                "taxes_id": [],
            }
        )
        so_form = Form(self.env["sale.order"].with_company(branch_xx))
        so_form.partner_id = self.partner
        with so_form.line_ids.new() as line:
            line.product_id = product_all_taxes
        with so_form.line_ids.new() as line:
            line.product_id = product_no_xx_tax
        with so_form.line_ids.new() as line:
            line.product_id = product_no_branch_tax
        with so_form.line_ids.new() as line:
            line.product_id = product_no_tax
        so = so_form.save()
        self.assertRecordValues(
            so.line_ids,
            [
                {"product_id": product_all_taxes.id, "tax_ids": tax_xx.ids},
                {"product_id": product_no_xx_tax.id, "tax_ids": tax_x.ids},
                {
                    "product_id": product_no_branch_tax.id,
                    "tax_ids": (tax_a + tax_b).ids,
                },
                {"product_id": product_no_tax.id, "tax_ids": []},
            ],
        )

    def test_price_recomputation_on_readonly_unit_price(self):
        self.pricelist.item_ids = [
            Command.create(
                {
                    "product_id": self.product.id,
                    "fixed_price": 22.0,
                    "min_quantity": 3.0,
                }
            )
        ]

        product_sol = self.sale_order.line_ids[0]
        self.assertNotEqual(product_sol.price_unit, 22)
        self.sale_order.write(
            {
                "line_ids": [
                    Command.update(
                        product_sol.id, {"product_qty": 4.0, "price_unit_auto": 22.0}
                    )
                ],
            }
        )
        self.assertEqual(product_sol.price_unit, 22.0)

        new_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_qty": 5.0,
                            "price_unit_auto": 22.0,
                        }
                    ),
                ],
            }
        )
        self.assertEqual(new_order.line_ids.price_unit, 22.0)

    def test_sale_warnings(self):
        partner_with_warning = self.env["res.partner"].create(
            {"name": "Test Partner", "sale_warn_msg": "Highly infectious disease"}
        )
        child_partner = self.env["res.partner"].create(
            {
                "type": "invoice",
                "parent_id": partner_with_warning.id,
                "sale_warn_msg": "Slightly infectious disease",
            }
        )
        sale_order = self.env["sale.order"].create(
            {"partner_id": partner_with_warning.id}
        )
        sale_order2 = self.env["sale.order"].create({"partner_id": child_partner.id})

        product_with_warning1 = self.env["product.product"].create(
            {"name": "Test Product 1", "sale_line_warn_msg": "Highly corrosive"}
        )
        product_with_warning2 = self.env["product.product"].create(
            {"name": "Test Product 2", "sale_line_warn_msg": "Toxic pollutant"}
        )
        self.env["sale.order.line"].create(
            [
                {
                    "order_id": sale_order.id,
                    "product_id": product_with_warning1.id,
                },
                {
                    "order_id": sale_order.id,
                    "product_id": product_with_warning2.id,
                },
                {
                    "order_id": sale_order.id,
                    "product_id": product_with_warning1.id,
                },
                {
                    "order_id": sale_order2.id,
                    "product_id": product_with_warning1.id,
                },
                {
                    "order_id": sale_order2.id,
                    "product_id": product_with_warning2.id,
                },
                {
                    "order_id": sale_order2.id,
                    "product_id": product_with_warning1.id,
                },
            ]
        )

        group_warning_sale = self.env.ref("sale.group_warning_sale")
        self.group_user.implied_ids = [Command.link(group_warning_sale.id)]
        sale_order2.action_confirm()
        sale_order2._create_invoices()
        invoice = Form(sale_order2.invoice_ids[0])

        expected_warnings = (
            "Test Partner - Highly infectious disease",
            "Test Product 1 - Highly corrosive",
            "Test Product 2 - Toxic pollutant",
        )
        expected_warnings_for_sale_order2 = (
            "Test Partner, Invoice - Slightly infectious disease",
            "Test Partner - Highly infectious disease",
            "Test Product 1 - Highly corrosive",
            "Test Product 2 - Toxic pollutant",
        )
        self.assertEqual(sale_order.sale_warning_text, "\n".join(expected_warnings))
        self.assertEqual(
            sale_order2.sale_warning_text, "\n".join(expected_warnings_for_sale_order2)
        )
        self.assertEqual(
            invoice.sale_warning_text, "\n".join(expected_warnings_for_sale_order2)
        )

        self.group_user.implied_ids = [Command.unlink(group_warning_sale.id)]
        self.assertEqual(sale_order.sale_warning_text, "")
        self.assertEqual(sale_order2.sale_warning_text, "")
        invoice = Form(sale_order2.invoice_ids[0])
        self.assertEqual(invoice.sale_warning_text, "")

    def test_sale_order_email_subtitle(self):
        partner = self.env["res.partner"].create(
            {"type": "invoice", "parent_id": self.partner.id}
        )
        self.sale_order.partner_id = partner
        context = self.sale_order._notify_by_email_prepare_rendering_context(
            message=self.env["mail.message"]
        )
        self.assertEqual(context["subtitles"][0], self.sale_order.name)

        self.sale_order.partner_id.name = "Test Partner"
        context = self.sale_order._notify_by_email_prepare_rendering_context(
            message=self.env["mail.message"]
        )
        self.assertEqual(
            context["subtitles"][0], f"{self.sale_order.name} - Test Partner"
        )

    def test_sale_order_unit_price_recompute_on_product_change(self):
        product2 = self.env["product.product"].create(
            {
                "name": "Test Product2",
                "list_price": 0.0,
            }
        )
        sol = self.sale_order.line_ids[0]
        with Form(sol) as sol_form:
            sol_form.product_id = product2
            sol_form.price_unit = 100
        self.assertAlmostEqual(
            sol.price_subtotal,
            100 * sol.product_uom_qty,
            msg="price_total should be equal to expected_total",
        )
        with Form(sol) as sol_form:
            sol_form.product_id = self.product
        self.assertAlmostEqual(
            sol.price_subtotal,
            self.product.list_price * sol.product_uom_qty,
            msg="price_total should be equal to expected_total",
        )

    def test_track_finalize_discard_keeps_other_records_pending_tracking(self):
        order_a, order_b = self.empty_order, self.sale_order
        tracking_key = f"mail.tracking.{order_a._name}"
        uid_key = f"mail.tracking.uid.{order_a._name}"
        precommit_data = self.env.cr.precommit.data
        precommit_data[tracking_key] = {
            order_a.id: {"state": "draft"},
            order_b.id: {"state": "draft"},
        }
        precommit_data[uid_key] = {
            order_a.id: self.env.uid,
            order_b.id: self.env.uid,
        }

        with patch.object(type(order_a), "_discard_tracking", return_value=True):
            order_a.env.cache.set(order_a, order_a._fields["state"], order_a.state)
            order_a._track_finalize()

        self.assertNotIn(
            order_a.id,
            precommit_data.get(tracking_key, {}),
            "the discarding order's own entry should be gone",
        )
        self.assertEqual(
            precommit_data.get(tracking_key, {}).get(order_b.id),
            {"state": "draft"},
            "another order's pending tracking must survive the discard",
        )


@tagged("post_install", "-at_install")
class TestSaleOrderInvoicing(AccountTestInvoicingCommon, SaleCommon):
    def test_invoice_state_when_ordered_quantity_is_negative(self):
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_qty": -1,
                        },
                    )
                ],
            }
        )
        sale_order.action_confirm()
        invoice = sale_order._create_invoices(final=True)
        invoice.action_post()
        self.assertTrue(
            sale_order.invoice_state == "done",
            'Sale: The invoicing status of the SO should be "done"',
        )


@tagged("post_install", "-at_install")
class TestSaleOrderCompany(SaleCommon):
    def test_sale_order_analytic_distribution_change(self):
        self.env.user.group_ids += self.env.ref("analytic.group_analytic_accounting")

        analytic_plan = self.env["account.analytic.plan"].create({"name": "Plan Test"})
        analytic_account_super = self.env["account.analytic.account"].create(
            {"name": "Super Account", "plan_id": analytic_plan.id}
        )
        analytic_account_great = self.env["account.analytic.account"].create(
            {"name": "Great Account", "plan_id": analytic_plan.id}
        )
        super_product = self.env["product.product"].create({"name": "Super Product"})
        great_product = self.env["product.product"].create({"name": "Great Product"})
        self.env["account.analytic.distribution.model"].create(
            [
                {
                    "analytic_distribution": {analytic_account_super.id: 100},
                    "product_id": super_product.id,
                },
                {
                    "analytic_distribution": {analytic_account_great.id: 100},
                    "product_id": great_product.id,
                },
            ]
        )
        partner = self.env["res.partner"].create({"name": "Test Partner"})
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
            }
        )
        sol = self.env["sale.order.line"].create(
            {
                "name": super_product.name,
                "product_id": super_product.id,
                "order_id": sale_order.id,
            }
        )

        self.assertEqual(
            sol.analytic_distribution,
            {str(analytic_account_super.id): 100},
            "The analytic distribution should be set to Super Account",
        )
        sol.write({"product_id": great_product.id})
        self.assertEqual(
            sol.analytic_distribution,
            {str(analytic_account_great.id): 100},
            "The analytic distribution should be set to Great Account",
        )

        product_no_model = self.env["product.product"].create(
            {"name": "Product No Model"}
        )
        sol_no_model = self.env["sale.order.line"].create(
            {
                "name": product_no_model.name,
                "product_id": product_no_model.id,
                "order_id": sale_order.id,
            }
        )
        self.assertFalse(
            sol_no_model.analytic_distribution,
            "A product without a matching distribution model should get no "
            "analytic distribution.",
        )

        so_no_analytic_account = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
            }
        )
        sol_no_analytic_account = self.env["sale.order.line"].create(
            {
                "name": super_product.name,
                "product_id": super_product.id,
                "order_id": so_no_analytic_account.id,
                "analytic_distribution": False,
            }
        )
        so_no_analytic_account.action_confirm()
        self.assertFalse(
            sol_no_analytic_account.analytic_distribution,
            "The compute should not overwrite what the user has set.",
        )

        sale_order.action_confirm()
        sol_on_confirmed_order = self.env["sale.order.line"].create(
            {
                "name": super_product.name,
                "product_id": super_product.id,
                "order_id": sale_order.id,
            }
        )

        self.assertEqual(
            sol_on_confirmed_order.analytic_distribution,
            {str(analytic_account_super.id): 100},
            "The analytic distribution should be set to Super Account, even for confirmed orders",
        )

    def test_cannot_assign_tax_of_mismatch_company(self):
        company_a = self.env["res.company"].create({"name": "A"})
        company_b = self.env["res.company"].create({"name": "B"})
        country = self.env["res.country"].search([], limit=1)
        tax_group_a = self.env["account.tax.group"].create(
            {
                "name": "A",
                "company_ids": [Command.set(company_a.ids)],
                "country_id": country.id,
            }
        )
        tax_group_b = self.env["account.tax.group"].create(
            {
                "name": "B",
                "company_ids": [Command.set(company_b.ids)],
                "country_id": country.id,
            }
        )

        tax_a = self.env["account.tax"].create(
            {
                "name": "A",
                "amount": 10,
                "company_ids": [Command.set(company_a.ids)],
                "tax_group_id": tax_group_a.id,
                "country_id": country.id,
            }
        )
        tax_b = self.env["account.tax"].create(
            {
                "name": "B",
                "amount": 10,
                "company_ids": [Command.set(company_b.ids)],
                "tax_group_id": tax_group_b.id,
                "country_id": country.id,
            }
        )

        sale_order = self.env["sale.order"].create(
            {"partner_id": self.partner.id, "company_id": company_a.id}
        )
        product = self.env["product.product"].create({"name": "Product"})

        sol = (
            self.env["sale.order.line"]
            .sudo()
            .create(
                {
                    "name": product.name,
                    "product_id": product.id,
                    "order_id": sale_order.id,
                    "tax_ids": tax_a,
                }
            )
        )

        with self.assertRaises(UserError):
            sol.tax_ids = tax_b

    def test_assign_tax_multi_company(self):
        root_company = self.env["res.company"].create({"name": "B0 company"})
        root_company.write(
            {
                "child_ids": [
                    Command.create({"name": "B1 company"}),
                    Command.create({"name": "B2 company"}),
                ]
            }
        )

        country = self.env["res.country"].search([], limit=1)
        basic_tax_group = self.env["account.tax.group"].create(
            {"name": "basic group", "country_id": country.id}
        )
        tax_b0 = self.env["account.tax"].create(
            {
                "name": "B0 tax",
                "company_ids": [Command.set(root_company.ids)],
                "amount": 10,
                "tax_group_id": basic_tax_group.id,
                "country_id": country.id,
            }
        )
        tax_b1 = self.env["account.tax"].create(
            {
                "name": "B1 tax",
                "company_ids": [Command.set(root_company.child_ids[0].ids)],
                "amount": 11,
                "tax_group_id": basic_tax_group.id,
                "country_id": country.id,
            }
        )
        tax_b2 = self.env["account.tax"].create(
            {
                "name": "B2 tax",
                "company_ids": [Command.set(root_company.child_ids[1].ids)],
                "amount": 20,
                "tax_group_id": basic_tax_group.id,
                "country_id": country.id,
            }
        )

        sale_order = self.env["sale.order"].create(
            {"partner_id": self.partner.id, "company_id": root_company.child_ids[0].id}
        )
        product = self.env["product.product"].create({"name": "Product"})

        sol_b1 = (
            self.env["sale.order.line"]
            .sudo()
            .create(
                {
                    "name": product.name,
                    "product_id": product.id,
                    "order_id": sale_order.id,
                    "tax_ids": tax_b1,
                }
            )
        )

        sol_b1.tax_ids = tax_b0
        sol_b1.tax_ids = tax_b1
        with self.assertRaises(UserError):
            sol_b1.tax_ids = tax_b2

    def test_downpayment_amount_constraints(self):
        self.sale_order.require_payment = True
        with self.assertRaises(ValidationError):
            self.sale_order.prepayment_percent = -1
        with self.assertRaises(ValidationError):
            self.sale_order.prepayment_percent = 1.01

    def test_action_view_source_sale_orders_single_order(self):
        self.sale_order.action_confirm()
        invoice = self.sale_order._create_invoices()
        action = invoice.action_view_source_sale_orders()
        self.assertEqual(action["res_id"], self.sale_order.id)
        view_id, view_mode = action["views"][0]
        self.assertEqual(view_mode, "form")
        self.assertTrue(view_id)

    def test_check_sale_product_company_blocks_restricting_used_product(self):
        other_company = self.env["res.company"].create({"name": "Other Co"})
        product = self.env["product.product"].create({"name": "Shared product"})
        self.env["sale.order.line"].create(
            {
                "order_id": self.sale_order.id,
                "product_id": product.id,
            }
        )
        with self.assertRaises(ValidationError):
            product.product_tmpl_id.company_id = other_company

    def test_qty_transferred_on_creation(self):
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                        }
                    )
                ],
            }
        )
        self.assertEqual(
            self.env["sale.order.line"].search(
                ["&", ("order_id", "=", sale_order.id), ("qty_transferred", "=", 0.0)]
            ),
            sale_order.line_ids,
        )

    def test_action_recompute_taxes(self):
        special_tax = self.env["account.tax"].create(
            {
                "name": "special_tax_10",
                "amount_type": "percent",
                "amount": 25.0,
                "include_base_amount": True,
                "price_include_override": "tax_included",
            }
        )

        mapping_a = self.env["account.fiscal.position"].create(
            {
                "name": "Special Tax Reduction",
            }
        )
        mapping_b = self.env["account.fiscal.position"].create(
            {
                "name": "Special Tax Reduction",
            }
        )
        self.env["account.tax"].create(
            {
                "name": "tax_a",
                "amount_type": "percent",
                "amount": 12.5,
                "include_base_amount": True,
                "price_include_override": "tax_included",
                "fiscal_position_ids": mapping_a,
                "original_tax_ids": special_tax,
            }
        )

        self.env["account.tax"].create(
            {
                "name": "tax_b",
                "amount_type": "percent",
                "amount": 5.0,
                "include_base_amount": True,
                "price_include_override": "tax_included",
                "fiscal_position_ids": mapping_b,
                "original_tax_ids": special_tax,
            }
        )

        sales_tax = self.env["account.tax"].create(
            {
                "name": "VAT 20%",
                "amount_type": "percent",
                "amount": 20.0,
                "price_include_override": "tax_included",
            }
        )

        self.product.write(
            {
                "lst_price": 300,
                "taxes_id": [Command.set((special_tax + sales_tax).ids)],
            }
        )

        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_qty": 1.0,
                        }
                    ),
                ],
            }
        )

        self.assertEqual(order.amount_total, 300)
        self.assertEqual(order.amount_tax, 100)
        order.fiscal_position_id = mapping_a
        order._recompute_prices()
        order.action_update_taxes()
        self.assertEqual(order.amount_total, 270)
        self.assertEqual(order.amount_tax, 70)
        order.fiscal_position_id = mapping_b
        order._recompute_prices()
        order.action_update_taxes()
        self.assertEqual(order.amount_total, 252)
        self.assertEqual(order.amount_tax, 52)


@tagged("post_install", "-at_install")
class TestSaleMailComposerUI(MailCommon, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["mail.alias.domain"].create({"name": "example.com"})
        cls.partner = cls.env["res.partner"].create(
            {"name": "test customer", "email": "dummy@example.com"}
        )
        cls.quotation = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
            }
        )

    def test_mail_attachment_removal_tour(self):
        url = f"/odoo/sales/{self.quotation.id}"
        with self.mock_mail_app():
            self.start_tour(
                url,
                "mail_attachment_removal_tour",
                login="admin",
            )


@tagged("post_install", "-at_install")
class TestResPartnerViewGroups(SaleCommon):
    def _combined_groups(self, xmlid, node_xpath):
        view = self.env.ref(xmlid)
        arch = view._get_combined_arch()
        node = arch.find(node_xpath)
        self.assertIsNotNone(
            node, f"{node_xpath!r} not found in {xmlid}'s combined arch"
        )
        return set((node.get("groups") or "").split(","))

    def test_fiscal_information_keeps_base_groups(self):
        groups = self._combined_groups(
            "account.view_partner_property_form", ".//group[@name='fiscal_information']"
        )
        self.assertIn("account.group_account_invoice", groups)
        self.assertIn("account.group_account_readonly", groups)
        self.assertIn("sale.group_sale_salesman", groups)

    def test_payment_term_fields_keep_base_groups(self):
        for field_name in (
            "property_payment_term_id",
            "property_supplier_payment_term_id",
        ):
            with self.subTest(field=field_name):
                groups = self._combined_groups(
                    "account.view_partner_property_form",
                    f".//field[@name='{field_name}']",
                )
                self.assertIn("account.group_account_invoice", groups)
                self.assertIn("account.group_account_readonly", groups)
                self.assertIn("sale.group_sale_salesman", groups)

    def test_saved_payment_methods_button_adds_group(self):
        view = self.env.ref("payment.view_partners_form_payment_defaultcreditcard")
        arch = view._get_combined_arch()
        action_id = self.env.ref("payment.action_payment_token").id
        button = arch.find(f".//button[@name='{action_id}']")
        self.assertIsNotNone(button)
        groups = set((button.get("groups") or "").split(","))
        self.assertIn("sale.group_sale_salesman", groups)


@tagged("post_install", "-at_install")
class TestAccountMoveSaleCustomerInvoiceDomain(SaleCommon):
    def _get_field_node_domain(self, xmlid, field_name):
        view = self.env.ref(xmlid)
        arch = view._get_combined_arch()
        node = arch.find(f".//field[@name='{field_name}']")
        self.assertIsNotNone(node)
        return node.get("domain")

    def test_domain_combines_partner_and_move_filters(self):
        domain_str = self._get_field_node_domain(
            "account.view_move_form", "sale_customer_invoice_id"
        )
        evaluated = safe_eval(
            domain_str,
            {
                "partner_id": 42,
                "commercial_partner_id": 42,
                "move_id": False,
                "move_type": "out_invoice",
            },
        )
        self.assertIn(("partner_id.commercial_partner_id", "=", 42), evaluated)
        self.assertIn("|", evaluated)
        self.assertIn(("move_id", "=", False), evaluated)
        self.assertIn(("move_id.move_type", "=", "out_invoice"), evaluated)


@tagged("post_install", "-at_install")
class TestAccountMoveComputeDepends(SaleCommon):
    def test_compute_sale_warning_text_depends_on_commercial_parent(self):
        AccountMove = self.env["account.move"]
        depends = self.env.registry.field_depends[
            AccountMove._fields["sale_warning_text"]
        ]
        self.assertIn("partner_id.parent_id.name", depends)
        self.assertIn("partner_id.parent_id.sale_warn_msg", depends)

    def test_compute_is_storno_depends_on_downpayment_not_on_the_company_flag(self):
        AccountMoveLine = self.env["account.move.line"]
        depends = self.env.registry.field_depends[AccountMoveLine._fields["is_storno"]]
        self.assertIn("is_downpayment", depends)
        self.assertNotIn("company_id.account_config_id.account_storno", depends)

    def test_invoiced_amount_excludes_subsection_lines(self):
        AccountMove = self.env["account.move"]
        source = inspect.getsource(AccountMove._get_sale_order_invoiced_amount)
        self.assertIn("line_subsection", source)


@tagged("post_install", "-at_install")
class TestPortalRulePermFlags(SaleCommon):
    def test_portal_rules_deny_write_create_unlink(self):
        for xmlid in (
            "sale.sale_order_rule_portal",
            "sale.sale_order_line_rule_portal",
        ):
            rule = self.env.ref(xmlid)
            with self.subTest(rule=xmlid):
                self.assertTrue(rule.perm_read)
                self.assertFalse(rule.perm_write)
                self.assertFalse(rule.perm_create)
                self.assertFalse(rule.perm_unlink)


@tagged("post_install", "-at_install")
class TestPriceHistoryWizardRule(SaleCommon):
    def test_wizard_is_scoped_to_its_creator(self):
        group = self.env.ref("sale.group_sale_salesman")
        user_a, user_b = self.env["res.users"].create(
            [
                {
                    "name": "F08 User A",
                    "login": "f08_user_a",
                    "group_ids": [(4, group.id)],
                },
                {
                    "name": "F08 User B",
                    "login": "f08_user_b",
                    "group_ids": [(4, group.id)],
                },
            ]
        )
        wizard = (
            self.env["sale.order.line.price.history"]
            .with_user(user_a)
            .create({"line_id": self.sale_order.line_ids[0].id})
        )

        found = (
            self.env["sale.order.line.price.history"]
            .with_user(user_b)
            .search([("id", "=", wizard.id)])
        )
        self.assertFalse(
            found, "another salesman must not see user_a's price-history wizard"
        )


@tagged("post_install", "-at_install")
class TestDownPaymentSectionLineLang(SaleCommon):
    def test_section_name_uses_partner_lang(self):
        self.env["res.lang"]._activate_lang("es_419")
        self.sale_order.partner_id.lang = "es_419"
        self.assertNotEqual(self.env.lang, "es_419")

        values = self.sale_order._prepare_down_payment_section_line()
        self.assertEqual(values["name"], "Anticipos")


@tagged("post_install", "-at_install")
class TestPaymentTermReadonly(SaleCommon):
    def test_payment_term_id_readonly_once_done(self):
        self.sale_order.action_confirm()
        self.assertEqual(self.sale_order.state, "done")

        with Form(self.sale_order) as order_form:
            with self.assertRaises(AssertionError):
                order_form.payment_term_id = self.env["account.payment.term"].search(
                    [], limit=1
                )


@tagged("post_install", "-at_install")
class TestSaleOrderLineDisplayName(SaleCommon):
    def test_display_name_switches_lang_when_partner_has_one(self):
        self.env["res.lang"]._activate_lang("es_419")
        self.sale_order.partner_id.lang = "es_419"
        line = self.sale_order.line_ids[0]
        line.invalidate_recordset(["display_name"])
        self.assertIn(self.sale_order.name, line.display_name)

    def test_display_name_unaffected_without_partner_lang(self):
        self.sale_order.partner_id.lang = False
        line = self.sale_order.line_ids[0]
        line.invalidate_recordset(["display_name"])
        self.assertIn(self.sale_order.name, line.display_name)


@tagged("post_install", "-at_install")
class TestPaymentLinkWizardWarning(SaleCommon):
    def test_expired_order_gets_warning_message(self):
        self.sale_order.date_validity = fields.Date.today() - timedelta(days=1)
        self.assertTrue(self.sale_order.is_expired)

        wizard = (
            self.env["payment.link.wizard"]
            .with_context(
                active_model="sale.order",
                active_id=self.sale_order.id,
            )
            .create({})
        )
        self.assertEqual(wizard.warning_message, "The sale order has expired.")
