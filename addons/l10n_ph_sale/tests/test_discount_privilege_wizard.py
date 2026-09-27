# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from odoo.addons.l10n_ph.tests.common import TestPhCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestDiscountPrivilegeWizard(TestPhCommon):
    """Only the behavior owned by l10n_ph_sale is covered here:

    * the wiring of the shared wizard onto sale orders (order anchoring,
      company/currency resolution, line autopopulation),
    * the sale.order.line hooks (gross-amount recompute, section/note skip,
      fiscal-position price/tax adaptation, restore),
    * propagation of the privilege to generated invoices,
    * the interplay with the standard sale Discounts wizard,
    * the salesman access rights defined by this module.

    The generic wizard flow (previews, scopes, onchanges, errors), the
    fiscal-position tax mappings, the privilege model and the discount math
    matrix are covered by l10n_ph_invoice and deliberately not retested.
    """

    @classmethod
    def get_default_groups(cls):
        groups = super().get_default_groups()
        return groups | cls.quick_ref("sales_team.group_sale_salesman")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        ChartTemplate = cls.env["account.chart.template"].with_company(
            cls.company_data["company"],
        )
        cls.tax_sale_12 = ChartTemplate.ref("l10n_ph_tax_sale_12")
        cls.tax_sale_0_exempt_sc_pwd = ChartTemplate.ref("l10n_ph_tax_sale_0_exempt_sc_pwd")
        cls.fpos_sc_pwd = ChartTemplate.ref("l10n_ph_fiscal_position_discount_privileges")
        cls.base_tax = cls.tax_sale_12

        cls.tax_incl = cls._create_tax("12% VAT INCL", 12, price_include_override="tax_included")
        cls.tax_sale_0_exempt_sc_pwd.write(
            {"original_tax_ids": [Command.link(cls.tax_incl.id)]},
        )
        cls.special_discount_account = cls.company_data["default_account_revenue"].copy(
            {"name": "Discount Privilege Account"},
        )
        cls.privilege = (
            cls.env["l10n_ph.discount.privilege"]
            .sudo()
            .create(
                {
                    "name": "Senior Citizen",
                    "discount_amount": 0.2,
                    "fiscal_position_id": cls.fpos_sc_pwd.id,
                    "account_id": cls.special_discount_account.id,
                },
            )
        )
        cls.privilege_without_tax = (
            cls.env["l10n_ph.discount.privilege"]
            .sudo()
            .create(
                {
                    "name": "Special Discount 20% No FP",
                    "discount_type": "special",
                    "discount_amount": 0.2,
                    "account_id": cls.special_discount_account.id,
                },
            )
        )

        cls.category_a = cls.env["product.category"].create({"name": "Category A"})
        cls.category_b = cls.env["product.category"].create({"name": "Category B"})
        cls.product_a = cls.env["product.product"].create(
            {"name": "Product A", "categ_id": cls.category_a.id, "list_price": 120.0},
        )
        cls.product_b = cls.env["product.product"].create(
            {"name": "Product B", "categ_id": cls.category_b.id, "list_price": 220.0},
        )

    # ============================================================
    #  Wizard wiring on sale orders
    # ============================================================

    def test_wizard_wiring_on_sale_order(self):
        """Opening the wizard from a sale order anchors it to the order,
        resolves company/currency from it, displays the SOL label/category,
        and autopopulates one wizard line per product line while excluding
        sections, notes and global discount lines."""
        sale_order = self._create_sale_order(
            confirm=False,
            order_line=[
                Command.create({"name": "Section Title", "display_type": "line_section"}),
                Command.create(
                    {
                        "name": "My SO Line",
                        "product_id": self.product_a.id,
                        "product_uom_qty": 1.0,
                        "price_unit": 100.0,
                        "tax_ids": [Command.set(self.base_tax.ids)],
                    },
                ),
                Command.create({"name": "Note", "display_type": "line_note"}),
            ],
        )
        # Add a global discount line: it must not receive a wizard line.
        self._apply_sale_discount(sale_order, "so_discount")

        action = sale_order.action_open_discount_privilege_wizard()
        self.assertEqual(action["res_model"], "l10n_ph.discount.privilege.wizard")
        wizard = self.env["l10n_ph.discount.privilege.wizard"].browse(action["res_id"])
        self.assertRecordValues(wizard, [{
            "order_id": sale_order.id,
            "move_id": False,
            "company_id": sale_order.company_id.id,
            "currency_id": sale_order.currency_id.id,
        }])

        product_line = sale_order.order_line.filtered(
            lambda sol: sol.product_id == self.product_a,
        )
        self.assertRecordValues(wizard.line_ids, [{
            "sale_order_line_id": product_line.id,
            "category_id": self.category_a.id,
        }])
        self.assertIn("Product A", wizard.line_ids.name)

    def test_create_with_both_document_fields_raises_error(self):
        sale_order = self._single_line_order()
        sale_order.action_confirm()
        invoice = sale_order._create_invoices()
        with self.assertRaises(ValidationError):
            self.env["l10n_ph.discount.privilege.wizard"].create(
                {"move_id": invoice.id, "order_id": sale_order.id},
            )

    # ============================================================
    #  Sale order line hooks
    # ============================================================

    def test_apply_privilege_adapts_price_and_restores(self):
        """Applying a fiscal-position privilege on a sale order line maps
        the taxes to the SC/PWD exempt ones and adapts the price unit
        (document_tax_mode comes from the order); removing it restores the
        original taxes, discount and price unit."""
        sale_order = self._create_sale_order_with_lines(
            (
                "Line A",
                self.product_a,
                750.0,
                {"tax_ids": self.tax_sale_12, "discount": 10.0},
            ),
            document_tax_mode="tax_included",
        )
        self._apply_privilege(sale_order, privilege_id=self.privilege.id, apply_on="all")

        line = sale_order.order_line
        # price_unit uses min_display_digits (view-only rounding), so
        # assertRecordValues cannot apply its usual float tolerance to it.
        self.assertAlmostEqual(line.price_unit, 669.64, places=2)
        self.assertRecordValues(line, [{
            "tax_ids": self.tax_sale_0_exempt_sc_pwd.ids,
            "l10n_ph_original_tax_ids": self.tax_sale_12.ids,
            "discount": 20.0,
            "l10n_ph_original_discount": 10.0,
            "l10n_ph_original_price_unit": 750.0,
            # Reported on the gross subtotal; never as a regular discount.
            "price_subtotal": 535.71,
            "l10n_ph_special_discount_amount": 133.93,
            "l10n_ph_regular_discount_amount": 0.0,
        }])

        # Removing the privilege restores everything on the SOL.
        self._create_wizard(sale_order).action_remove_all()
        self.assertAlmostEqual(line.price_unit, 750.0, places=2)
        self.assertRecordValues(line, [{
            "l10n_ph_discount_privilege_id": False,
            "tax_ids": self.base_tax.ids,
            "l10n_ph_original_tax_ids": [],
            "discount": 10.0,
            "l10n_ph_original_price_unit": 0.0,
            "l10n_ph_original_discount": 0.0,
        }])

    def test_special_privilege_reports_on_gross_total(self):
        """Without a fiscal position the line keeps its taxes and a 'special'
        privilege reports its discount on the gross VAT-included total —
        even at 100%, where price_subtotal alone would be zero."""
        sale_order = self._single_line_order()
        self._apply_privilege(
            sale_order,
            privilege_id=self.privilege_without_tax.id,
            apply_on="all",
        )

        line = sale_order.order_line
        self.assertRecordValues(line, [{
            "tax_ids": self.base_tax.ids,
            "price_subtotal": 80.0,
            "price_total": 89.6,
            "l10n_ph_special_discount_amount": 22.4,
            "l10n_ph_regular_discount_amount": 0.0,
        }])

        full = self._create_privilege("Full Special", 1.0, discount_type="special")
        sale_order = self._single_line_order()
        self._apply_privilege(sale_order, privilege_id=full.id, apply_on="all")

        line = sale_order.order_line
        self.assertRecordValues(line, [{
            "discount": 100.0,
            "price_subtotal": 0.0,
            "l10n_ph_special_discount_amount": 112.0,
        }])

    # ============================================================
    #  Order-level computed field & state guards
    # ============================================================

    def test_state_guards_and_button_visibility(self):
        """l10n_ph_has_discount_privilege reflects privileged lines on
        draft/sent orders only, and the wizard rejects confirmed orders."""
        sale_order = self._single_line_order()
        self.assertRecordValues(sale_order, [{"l10n_ph_has_discount_privilege": False}])

        # Sent orders remain modifiable.
        sale_order.write({"state": "sent"})
        self._apply_privilege(sale_order, privilege_id=self.privilege.id, apply_on="all")
        self.assertRecordValues(sale_order.order_line, [{
            "l10n_ph_discount_privilege_id": self.privilege.id,
        }])
        self.assertRecordValues(sale_order, [{"l10n_ph_has_discount_privilege": True}])

        # Confirmed orders reject both apply and remove actions...
        sale_order.action_confirm()
        wizard = self._create_wizard(sale_order)
        with self.assertRaises(UserError):
            wizard.action_confirm()
        with self.assertRaises(UserError):
            wizard.action_remove_all()
        # ...and no longer advertise the button state.
        self.assertRecordValues(sale_order, [{"l10n_ph_has_discount_privilege": False}])

    # ============================================================
    #  Invoice propagation (sale-order specific behaviour)
    # ============================================================

    def test_invoice_propagation(self):
        """Privileged order lines generate invoice lines carrying the
        privilege and its original values; posting routes the discount
        allocation to the privilege account."""
        sale_order = self._create_sale_order_with_lines(
            ("Line A", self.product_a, 100.0, {"discount": 10.0}),
        )
        self._apply_privilege(sale_order, privilege_id=self.privilege.id, apply_on="all")

        sale_order.action_confirm()
        invoice = sale_order._create_invoices()
        inv_line = invoice.invoice_line_ids
        self.assertRecordValues(inv_line, [{
            "l10n_ph_discount_privilege_id": self.privilege.id,
            "tax_ids": self.tax_sale_0_exempt_sc_pwd.ids,
            "l10n_ph_original_price_unit": 100.0,
            "l10n_ph_original_discount": 10.0,
            "discount": 20.0,
            "price_subtotal": 80.0,
        }])

        # Posting routes the discount allocation to the privilege account.
        invoice.action_post()
        discount_lines = invoice.line_ids.filtered(
            lambda line_item: line_item.display_type == "discount",
        ).sorted("amount_currency")
        self.assertRecordValues(
            discount_lines,
            [
                {"account_id": inv_line.account_id.id, "amount_currency": -20.0},
                {"account_id": self.special_discount_account.id, "amount_currency": 20.0},
            ],
        )

    def test_invoice_propagation_restores_on_invoice(self):
        """Removing the privilege on the generated (draft) invoice restores
        the original values propagated from the sale order."""
        sale_order = self._create_sale_order_with_lines(
            ("Line A", self.product_a, 100.0, {"discount": 10.0}),
        )
        self._apply_privilege(sale_order, privilege_id=self.privilege.id, apply_on="all")

        sale_order.action_confirm()
        invoice = sale_order._create_invoices()
        inv_line = invoice.invoice_line_ids
        self.assertRecordValues(inv_line, [{
            "l10n_ph_discount_privilege_id": self.privilege.id,
        }])

        self._create_wizard(invoice).action_remove_all()
        self.assertRecordValues(inv_line, [{
            "l10n_ph_discount_privilege_id": False,
            "discount": 10.0,
            "tax_ids": self.tax_sale_12.ids,
        }])
        self.assertAlmostEqual(inv_line.price_unit, 100.0, places=2)

    # ============================================================
    #  Sale Discounts Interplay (no double discounting)
    # ============================================================

    def test_sale_discounts_skip_privileged_lines(self):
        """Privileged lines are excluded from the standard sale Discounts
        wizard, both for per-line and global discounts."""
        sale_order = self._create_sale_order_with_lines(
            ("Line A", self.product_a, 100.0, {"discount": 10.0}),
            ("Line B", self.product_b, 200.0, {"discount": 0.0}),
        )
        self._apply_privilege_to_products(sale_order, self.privilege, self.product_a)
        privileged = sale_order.order_line.filtered("l10n_ph_discount_privilege_id")
        self.assertEqual(len(privileged), 1)
        self.assertRecordValues(privileged, [{"discount": 20.0}])

        # Per-line discount: the privileged line keeps its privilege discount.
        self._apply_sale_discount(sale_order, "sol_discount")

        line_a = sale_order.order_line.filtered(lambda line: line.product_id == self.product_a)
        line_b = sale_order.order_line.filtered(lambda line: line.product_id == self.product_b)
        self.assertRecordValues(line_a, [{"discount": 20.0}])
        self.assertRecordValues(line_b, [{"discount": 10.0}])

        # Global discount: computed on the non-privileged lines only.
        sale_order = self._create_two_line_order()
        self._apply_privilege_to_products(sale_order, self.privilege, self.product_a)
        privileged = sale_order.order_line.filtered("l10n_ph_discount_privilege_id")
        self.assertEqual(len(privileged), 1)
        self.assertRecordValues(privileged, [{"discount": 20.0}])

        self._apply_sale_discount(sale_order, "so_discount")

        # The privileged line's discount is unchanged by the global discount.
        self.assertRecordValues(privileged, [{"discount": 20.0}])
        # A global discount line was still created for the remaining
        # (non-privileged) lines.
        discount_product = sale_order.company_id.sale_discount_product_id
        self.assertTrue(
            sale_order.order_line.filtered(lambda line: line.product_id == discount_product),
        )

    # ============================================================
    #  Access rights (module security/ir.access.csv)
    # ============================================================

    def test_salesman_can_apply_but_not_configure_privileges(self):
        salesman = new_test_user(
            self.env,
            login="salesman@example.com",
            groups="sales_team.group_sale_salesman",
            company_id=self.company_data["company"].id,
        )
        sale_order = self._single_line_order()
        wizard = (
            self.env["l10n_ph.discount.privilege.wizard"]
            .with_user(salesman)
            .with_context(
                active_id=sale_order.id,
                active_ids=[sale_order.id],
                active_model="sale.order",
            )
            .create({"order_id": sale_order.id})
        )
        self.assertRecordValues(wizard.line_ids, [{
            "sale_order_line_id": sale_order.order_line.id,
        }])

        # Salesmen can apply via wizard but cannot configure privileges.
        with self.assertRaises(AccessError):
            self.env["l10n_ph.discount.privilege"].with_user(salesman).create(
                {
                    "name": "Salesman Creates",
                    "discount_amount": 0.1,
                    "account_id": self.special_discount_account.id,
                    "company_id": self.company_data["company"].id,
                },
            )

        # A plain internal user without sales access has no access at all:
        # cannot read privilege definitions nor open/use the wizard.
        plain_user = new_test_user(
            self.env,
            login="plain.user@example.com",
            groups="base.group_user",
            company_id=self.company_data["company"].id,
        )
        with self.assertRaises(AccessError):
            self.env["l10n_ph.discount.privilege"].with_user(plain_user).search(
                [("id", "=", self.privilege.id)],
            )
        with self.assertRaises(AccessError):
            self.env["l10n_ph.discount.privilege.wizard"].with_user(plain_user).create(
                {"order_id": sale_order.id, "apply_on": "all"},
            )

    # ============================================================
    #  Helpers
    # ============================================================

    @classmethod
    def _create_tax(cls, name, amount, price_include_override=None):
        """Create a simple percentage sale tax."""
        return cls.env["account.tax"].create(
            {
                "name": name,
                "amount": amount,
                "type_tax_use": "sale",
                "price_include_override": price_include_override,
            },
        )

    @classmethod
    def _create_privilege(cls, name, discount_amount, *, discount_type="pwd", fiscal_position_id=None):
        """Create a discount privilege for the test company."""
        return (
            cls.env["l10n_ph.discount.privilege"]
            .sudo()
            .create(
                {
                    "name": name,
                    "discount_amount": discount_amount,
                    "discount_type": discount_type,
                    "fiscal_position_id": fiscal_position_id.id
                    if fiscal_position_id
                    else False,
                    "account_id": cls.special_discount_account.id,
                },
            )
        )

    @classmethod
    def _create_sale_order_with_lines(cls, *lines, **kwargs):
        """Create a draft sale order from ``(name, product, price_unit[, line_vals])`` specs."""
        order_line = []
        for line in lines:
            name, product, price_unit = line[:3]
            line_values = dict(line[3]) if len(line) > 3 else {}
            quantity = line_values.pop("quantity", 1.0)
            order_line.append(
                Command.create(
                    {
                        "name": name,
                        "product_id": product.id,
                        "product_uom_qty": quantity,
                        "price_unit": price_unit,
                        **line_values,
                    },
                ),
            )
        return cls._create_sale_order(confirm=False, order_line=order_line, **kwargs)

    @classmethod
    def _create_two_line_order(cls, **kwargs):
        """Create the standard two-line order: Product A (100.0) on Category A
        and Product B (200.0) on Category B."""
        return cls._create_sale_order_with_lines(
            ("Line A", cls.product_a, 100.0),
            ("Line B", cls.product_b, 200.0),
            **kwargs,
        )

    def _create_wizard(self, sale_order, **vals):
        """Open the wizard on ``sale_order`` like the button does, then apply ``vals``."""
        action = sale_order.action_open_discount_privilege_wizard()
        wizard = self.env["l10n_ph.discount.privilege.wizard"].browse(action["res_id"])
        if vals:
            wizard.write(vals)
        return wizard

    def _apply_privilege(self, sale_order, **vals):
        """Open the wizard, apply ``vals`` and confirm; returns the wizard."""
        wizard = self._create_wizard(sale_order, **vals)
        wizard.action_confirm()
        return wizard

    def _apply_privilege_to_products(self, sale_order, privilege, products):
        """Apply ``privilege`` to ``products`` through the wizard."""
        return self._apply_privilege(
            sale_order,
            privilege_id=privilege.id,
            apply_on="product",
            product_ids=[Command.set(products.ids)],
        )

    def _apply_sale_discount(self, sale_order, discount_type, percentage=0.1):
        """Apply the standard sale Discounts wizard on the order."""
        self.env["sale.order.discount"].create(
            {
                "sale_order_id": sale_order.id,
                "discount_type": discount_type,
                "discount_percentage": percentage,
            },
        ).action_apply_discount()

    def _single_line_order(self):
        """Return a new order with only one product line."""
        return self._create_sale_order_with_lines(
            ("Line A", self.product_a, 100.0),
        )
