# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestEstateProperty(AccountTestInvoicingCommon):
    # A salesperson without invoicing rights must still be able to sell
    _test_user_groups = ("base.group_user",)

    def test_selling_property_invoices_commission_and_administrative_fees(self):
        estate_property = self.env["estate.property"].create({
            "name": "Test House",
            "expected_price": 100000,
        })
        self.env["estate.property.offer"].create({
            "property_id": estate_property.id,
            "partner_id": self.partner_a.id,
            "price": 100000,
        }).action_accept()

        estate_property.action_sold()

        # The test user cannot read invoices: search them as superuser
        invoice = self.env["account.move"].sudo().search([("partner_id", "=", self.partner_a.id)])
        self.assertEqual(invoice.invoice_line_ids.mapped("price_unit"), [6000, 100])
