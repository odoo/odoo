# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import count

from odoo import Command

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_ph_invoice.models.l10n_ph_discount_privilege import (
    PARTNER_IDENTIFIER_KEYS,
)
from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon

_id_numbers = count(1)


def make_holder_vals(env, privilege, name=None, id_number=None):
    """
    Holder values, as sent by the POS, for the contact named ``name`` (created
    as needed, or generated when unset), given ``id_number`` as their ID of
    ``privilege``'s type (or keeping the one they already have, or a generated
    one when unset).
    """
    number = next(_id_numbers)
    name = name or f"ID Holder {number}"
    partner = env["res.partner"].search([("name", "=", name)], limit=1) or env["res.partner"].create({"name": name})
    identifiers = partner.additional_identifiers or {}
    key = PARTNER_IDENTIFIER_KEYS[privilege.discount_type]
    partner.additional_identifiers = {**identifiers, key: id_number or identifiers.get(key) or f"ID-{number}"}
    return {"privilege_id": privilege.id, "partner_id": partner.id}


class TestPosDiscountPrivilegeCommon(TestPoSCommon):
    """
    A Philippine company with an open session of its basic POS config, the
    SC and PWD privileges, and a pizza (1,000.00) and a soda (100.00), both
    taxed 12% (VAT excluded from the price unless a test says otherwise).
    """

    @classmethod
    @AccountTestInvoicingCommon.setup_country("ph")
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.basic_config
        ChartTemplate = cls.env["account.chart.template"].with_company(cls.company)
        cls.tax_sale_12 = ChartTemplate.ref("l10n_ph_tax_sale_12")
        cls.tax_sale_0_exempt_sc_pwd = ChartTemplate.ref("l10n_ph_tax_sale_0_exempt_sc_pwd")
        cls.privilege_sc = ChartTemplate.ref("l10n_ph_discount_privilege_sc_20_vat_incl")
        cls.privilege_pwd = ChartTemplate.ref("l10n_ph_discount_privilege_pwd_20_vat_incl")
        cls.pizza = cls.create_product("Pizza Margherita", cls.categ_basic, 1000.0, tax_ids=cls.tax_sale_12.ids)
        cls.soda = cls.create_product("Coca-Cola", cls.categ_basic, 100.0, tax_ids=cls.tax_sale_12.ids)

    def setUp(self):
        super().setUp()
        self.open_new_session()

    def _holder_vals(self, privilege, name=None, id_number=None):
        return make_holder_vals(self.env, privilege, name, id_number)

    def _create_order(self, order_lines, **kwargs):
        """A draft order of the open session, as synced by the POS.

        :param order_lines: pairs of (product, quantity)
        :param kwargs: further arguments of create_ui_order_data
        """
        data = self.create_ui_order_data(order_lines, payments=[], pos_order_ui_args={"state": "draft"}, **kwargs)
        return self.env["pos.order"].browse(self.env["pos.order"].sync_from_ui([data])["pos.order"][0]["id"])

    def _add_order_line(self, order, product, qty):
        line = self.env["pos.order.line"].create({
            "order_id": order.id,
            "product_id": product.id,
            "qty": qty,
            "price_unit": product.lst_price,
            "tax_ids": [Command.set(product.taxes_id.ids)],
            "price_subtotal": 0.0,
            "price_subtotal_incl": 0.0,
        })
        line._onchange_amount_line_all()
        return line

    def _create_combo_order(self):
        """An order of a combo (a pizza as its only choice) and a soda."""
        combo = self.env["product.combo"].create({
            "name": "Combo Choice",
            "company_id": self.company.id,
            "combo_item_ids": [Command.create({"product_id": self.pizza.id})],
        })
        combo_product = self.env["product.product"].create(
            {"name": "Combo", "type": "combo", "combo_ids": [Command.set(combo.ids)], "company_id": self.company.id},
        )
        order = self._create_order([(combo_product, 1.0), (self.soda, 2.0)])
        combo_line = order.lines[0]
        combo_child = self._add_order_line(order, self.pizza, 1.0)
        combo_child.combo_parent_id = combo_line
        return order, combo_line, combo_child

    def _send_to_preparation(self, line, quantity, cancelled=0.0):
        prep_order = self.env["pos.prep.order"].create({"pos_order_id": line.order_id.id})
        self.env["pos.prep.line"].create({
            "prep_order_id": prep_order.id,
            "pos_order_line_id": line.id,
            "product_id": line.product_id.id,
            "quantity": quantity,
            "cancelled": cancelled,
        })

    def _get_sent_qty(self, line):
        return sum(prep_line.quantity - prep_line.cancelled for prep_line in line.prep_line_ids)


class TestPosDiscountPrivilegeHttpCommon(TestPointOfSaleHttpCommon):
    """
    The tours' data: Juan Dela Cruz, a Senior Citizen, and a soda (100.00,
    taxed 12%) sold by the main POS config, on a Philippine company.
    """

    @classmethod
    @AccountTestInvoicingCommon.setup_country("ph")
    def setUpClass(cls):
        super().setUpClass()
        ChartTemplate = cls.env["account.chart.template"].with_company(cls.env.company)
        cls.tax_sale_12 = ChartTemplate.ref("l10n_ph_tax_sale_12")
        cls.privilege_sc = ChartTemplate.ref("l10n_ph_discount_privilege_sc_20_vat_incl")
        cls.privilege_pwd = ChartTemplate.ref("l10n_ph_discount_privilege_pwd_20_vat_incl")
        cls.juan = cls.env["res.partner"].create({
            "name": "Juan Dela Cruz",
            "country_id": cls.env.ref("base.ph").id,
            "additional_identifiers": {"PH_SC_ID": "SC-REG-001"},
        })
        cls.soda = cls.env["product.template"].create({
            "name": "Test Soda",
            "available_in_pos": True,
            "list_price": 100.0,
            "taxes_id": [Command.set(cls.tax_sale_12.ids)],
        })
