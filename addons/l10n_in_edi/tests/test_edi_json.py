# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestEdiJson(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].set_param('l10n_in_edi.manage_invoice_negative_lines', True)
        cls.maxDiff = None

        cls.partner_a.l10n_in_gst_treatment = "regular"

        cls.product_a_discount = cls.env['product.product'].create({
            'name': 'product_a discount',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'lst_price': 400.0,
            'standard_price': 400.0,
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
            'property_account_expense_id': cls.company_data['default_account_expense'].id,
            'taxes_id': [Command.set(cls.sgst_sale_5.ids)],
            'supplier_taxes_id': [Command.set(cls.sgst_purchase_5.ids)],
            "l10n_in_hsn_code": "111111",
        })
        gst_with_cess = cls.env.ref("account.%s_sgst_sale_12" % (cls.company_data["company"].id)
            ) + cls.env.ref("account.%s_cess_5_plus_1591_sale" % (cls.company_data["company"].id))
        product_with_cess = cls.env["product.product"].create({
            "name": "product_with_cess",
            "uom_id": cls.env.ref("uom.product_uom_unit").id,
            "lst_price": 1000.0,
            "standard_price": 800.0,
            "property_account_income_id": cls.company_data["default_account_revenue"].id,
            "property_account_expense_id": cls.company_data["default_account_expense"].id,
            "taxes_id": [Command.set(gst_with_cess.ids)],
            "supplier_taxes_id": [Command.set(cls.sgst_purchase_5.ids)],
            "l10n_in_hsn_code": "333333",
        })
        rounding = cls.env["account.cash.rounding"].create({
            "name": "half-up",
            "rounding": 1.0,
            "strategy": "add_invoice_line",
            "profit_account_id": cls.company_data['default_account_expense'].id,
            "loss_account_id": cls.company_data['default_account_expense'].id,
            "rounding_method": "HALF-UP",
        })
        cls.invoice = cls.init_invoice("out_invoice", post=False, products=cls.product_a + product_with_cess)
        cls.invoice.write({
            "invoice_line_ids": [(1, l_id, {"discount": 10}) for l_id in cls.invoice.invoice_line_ids.ids]})
        cls.invoice.action_post()
        cls.invoice_full_discount = cls.init_invoice("out_invoice", post=False, products=cls.product_a)
        cls.invoice_full_discount.write({
            "invoice_line_ids": [(1, l_id, {"discount": 100}) for l_id in cls.invoice_full_discount.invoice_line_ids.ids]})
        cls.invoice_full_discount.action_post()
        cls.invoice_zero_qty = cls.init_invoice("out_invoice", post=False, products=cls.product_a)
        cls.invoice_zero_qty.write({
            "invoice_line_ids": [(1, l_id, {"quantity": 0}) for l_id in cls.invoice_zero_qty.invoice_line_ids.ids]})
        cls.invoice_zero_qty.action_post()
        cls.invoice_negative_unit_price = cls.init_invoice("out_invoice", post=False, products=cls.product_a + cls.product_a_discount + product_with_cess)
        cls.invoice_negative_unit_price.write({
            "invoice_line_ids": [
                (1, cls.invoice_negative_unit_price.invoice_line_ids[0].id, {"price_unit": 1000}),
                (1, cls.invoice_negative_unit_price.invoice_line_ids[1].id, {"price_unit": -400}),
            ]})
        cls.invoice_negative_unit_price.action_post()
        cls.invoice_negative_qty = cls.init_invoice("out_invoice", post=False, products=cls.product_a + cls.product_a_discount + product_with_cess)
        cls.invoice_negative_qty.write({
            "invoice_line_ids": [
                (1, cls.invoice_negative_qty.invoice_line_ids[0].id, {"price_unit": 1000}),
                (1, cls.invoice_negative_qty.invoice_line_ids[1].id, {"price_unit": 400, 'quantity': -1}),
            ]})
        cls.invoice_negative_qty.action_post()
        cls.invoice_negative_unit_price_and_qty = cls.init_invoice("out_invoice", post=False, products=cls.product_a + cls.product_a_discount + product_with_cess)
        cls.invoice_negative_unit_price_and_qty.write({
            "invoice_line_ids": [
                (1, cls.invoice_negative_unit_price_and_qty.invoice_line_ids[0].id, {"price_unit": -1000, 'quantity': -1}),
                (1, cls.invoice_negative_unit_price_and_qty.invoice_line_ids[1].id, {"price_unit": -400}),
            ]})
        cls.invoice_negative_unit_price_and_qty.action_post()
        cls.invoice_negative_with_discount = cls.init_invoice("out_invoice", post=False, products=cls.product_a + cls.product_a_discount)
        cls.invoice_negative_with_discount.write({
            "invoice_line_ids": [
                (1, cls.invoice_negative_with_discount.invoice_line_ids[0].id, {"price_unit": 2000, 'discount': 50}),
                (1, cls.invoice_negative_with_discount.invoice_line_ids[1].id, {"price_unit": -400}),
            ]})
        cls.invoice_negative_with_discount.action_post()
        cls.invoice_negative_more_than_max_line = cls.init_invoice("out_invoice", post=False, products=cls.product_a + cls.product_b + cls.product_a_discount)
        cls.invoice_negative_more_than_max_line.write({
            "invoice_line_ids": [
                (1, cls.invoice_negative_more_than_max_line.invoice_line_ids[0].id, {"price_unit": 2000, 'discount': 50}),
                (1, cls.invoice_negative_more_than_max_line.invoice_line_ids[1].id, {"price_unit": 1000}),
                (1, cls.invoice_negative_more_than_max_line.invoice_line_ids[2].id, {"price_unit": -1100}),
            ]})
        cls.invoice_negative_more_than_max_line.action_post()
        cls.invoice_cash_rounding = cls.init_invoice("out_invoice", post=False, products=cls.product_a + product_with_cess)
        cls.invoice_cash_rounding.write({
            "invoice_line_ids": [(1, l_id, {"discount": 10}) for l_id in cls.invoice_cash_rounding.invoice_line_ids.ids],
            "invoice_cash_rounding_id": rounding.id,
        })
        cls.invoice_cash_rounding.action_post()

    def test_edi_json(self):
        # line1: 1000, 10% discount and a tax of 5%
        # line2: 1000, 10% discount and 4 taxes: 5%, 1.591, 6% SGST 6% CGST, each one affecting the base:
        # 900 * 1.05 = 945
        # 945 + 1.591 ~= 946.59
        # 946.59 * 0.06 = 56.80
        # total tax: 160.19
        json_value = self.env["account.edi.format"]._l10n_in_edi_generate_invoice_json(self.invoice)
        expected = {
            "Version": "1.1",
            "TranDtls": {"TaxSch": "GST", "SupTyp": "B2B", "RegRev": "N", "IgstOnIntra": "N"},
            "DocDtls": {"Typ": "INV", "No": "INV/18-19/0002", "Dt": "01/01/2019"},
            "SellerDtls": {
                "Addr1": "Khodiyar Chowk",
                "Loc": "Amreli",
                "Pin": 365220,
                "Stcd": "24",
                "Addr2": "Sala Number 3",
                "LglNm": "Default Company",
                "GSTIN": "24AAGCC7144L6ZE"},
            "BuyerDtls": {
                "Addr1": "Karansinhji Rd",
                "Loc": "Rajkot",
                "Pin": 360001,
                "Stcd": "24",
                "Addr2": "Karanpara",
                "POS": "24",
                "LglNm": "Partner Intra State",
                "GSTIN": "24ABCPM8965E1ZE"},
            "ItemList": [
                {
                    "SlNo": "1", "PrdDesc": "product_a", "IsServc": "N", "HsnCd": "111111", "Qty": 1.0,
                    "Unit": "UNT", "UnitPrice": 1000.0, "TotAmt": 1000.0, "Discount": 100.0, "AssAmt": 900.0,
                    "GstRt": 5.0, "IgstAmt": 0.0, "CgstAmt": 22.5, "SgstAmt": 22.5, "CesRt": 0.0, "CesAmt": 0.0,
                    "CesNonAdvlAmt": 0.0, "StateCesRt": 0.0, "StateCesAmt": 0.0, "StateCesNonAdvlAmt": 0.0,
                    "OthChrg": 0.0, "TotItemVal": 945.0
                },
                {
                    "SlNo": "2", "PrdDesc": "product_with_cess", "IsServc": "N", "HsnCd": "333333", "Qty": 1.0,
                    "Unit": "UNT", "UnitPrice": 1000.0, "TotAmt": 1000.0, "Discount": 100.0, "AssAmt": 900.0,
                    "GstRt": 12.0, "IgstAmt": 0.0, "CgstAmt": 56.8, "SgstAmt": 56.8, "CesRt": 5.0, "CesAmt": 45.0,
                    "CesNonAdvlAmt": 1.59, "StateCesRt": 0.0, "StateCesAmt": 0.0, "StateCesNonAdvlAmt": 0.0,
                    "OthChrg": 0.0, "TotItemVal": 1060.19
                }
            ],
            "ValDtls": {
                "AssVal": 1800.0, "CgstVal": 79.3, "SgstVal": 79.3, "IgstVal": 0.0, "CesVal": 46.59,
                "StCesVal": 0.0, "Discount": 0.0, "RndOffAmt": 0.0, "TotInvVal": 2005.19
            }
        }
        self.assertDictEqual(json_value, expected, "Indian EDI send json value is not matched")
        expected_copy_rounding = expected.copy()
        #=================================== Full discount test =====================================
        json_value = self.env["account.edi.format"]._l10n_in_edi_generate_invoice_json(self.invoice_full_discount)
        expected.update({
            "DocDtls": {"Typ": "INV", "No": "INV/18-19/0003", "Dt": "01/01/2019"},
            "ItemList": [{
                "SlNo": "1", "PrdDesc": "product_a", "IsServc": "N", "HsnCd": "111111", "Qty": 1.0,
                "Unit": "UNT", "UnitPrice": 1000.0, "TotAmt": 1000.0, "Discount": 1000.0, "AssAmt": 0.0,
                "GstRt": 0.0, "IgstAmt": 0.0, "CgstAmt": 0.0, "SgstAmt": 0.0, "CesRt": 0.0, "CesAmt": 0.0,
                "CesNonAdvlAmt": 0.0, "StateCesRt": 0.0, "StateCesAmt": 0.0, "StateCesNonAdvlAmt": 0.0,
                "OthChrg": 0.0, "TotItemVal": 0.0}],
            "ValDtls": {"AssVal": 0.0, "CgstVal": 0.0, "SgstVal": 0.0, "IgstVal": 0.0, "CesVal": 0.0,
                "StCesVal": 0.0, "Discount": 0.0, "RndOffAmt": 0.0, "TotInvVal": 0.0}
        })
        self.assertDictEqual(json_value, expected, "Indian EDI with 100% discount sent json value is not matched")

        #=================================== Zero quantity test =============================================
        json_value = self.env["account.edi.format"]._l10n_in_edi_generate_invoice_json(self.invoice_zero_qty)
        expected.update({
            "DocDtls": {"Typ": "INV", "No": "INV/18-19/0004", "Dt": "01/01/2019"},
            "ItemList": [{
                "SlNo": "1", "PrdDesc": "product_a", "IsServc": "N", "HsnCd": "111111", "Qty": 0.0,
                "Unit": "UNT", "UnitPrice": 1000.0, "TotAmt": 0.0, "Discount": 0.0, "AssAmt": 0.0,
                "GstRt": 0.0, "IgstAmt": 0.0, "CgstAmt": 0.0, "SgstAmt": 0.0, "CesRt": 0.0, "CesAmt": 0.0,
                "CesNonAdvlAmt": 0.0, "StateCesRt": 0.0, "StateCesAmt": 0.0, "StateCesNonAdvlAmt": 0.0,
                "OthChrg": 0.0, "TotItemVal": 0.0}],
        })
        self.assertDictEqual(json_value, expected, "Indian EDI with 0(zero) quantity sent json value is not matched")

        #=================================== Negative unit price test =============================================
        json_value = self.env["account.edi.format"]._l10n_in_edi_generate_invoice_json(self.invoice_negative_unit_price)
        expected.update({
            "DocDtls": {"Typ": "INV", "No": "INV/18-19/0005", "Dt": "01/01/2019"},
            "ItemList": [
                {
                    "SlNo": "1", "PrdDesc": "product_a", "IsServc": "N", "HsnCd": "111111", "Qty": 1.0,
                    "Unit": "UNT", "UnitPrice": 1000.0, "TotAmt": 1000.0, "Discount": 400.0, "AssAmt": 600.0,
                    "GstRt": 5.0, "IgstAmt": 0.0, "CgstAmt": 15.0, "SgstAmt": 15.0, "CesRt": 0.0, "CesAmt": 0.0,
                    "CesNonAdvlAmt": 0.0, "StateCesRt": 0.0, "StateCesAmt": 0.0, "StateCesNonAdvlAmt": 0.0,
                    "OthChrg": 0.0, "TotItemVal": 630.0
                },
                {
                    "SlNo": "3", "PrdDesc": "product_with_cess", "IsServc": "N", "HsnCd": "333333", "Qty": 1.0,
                    "Unit": "UNT", "UnitPrice": 1000.0, "TotAmt": 1000.0, "Discount": 0.0, "AssAmt": 1000.0,
                    "GstRt": 12.0, "IgstAmt": 0.0, "CgstAmt": 63.1, "SgstAmt": 63.1, "CesRt": 5.0, "CesAmt": 50.0,
                    "CesNonAdvlAmt": 1.59, "StateCesRt": 0.0, "StateCesAmt": 0.0, "StateCesNonAdvlAmt": 0.0,
                    "OthChrg": 0.0, "TotItemVal": 1177.79
                }
            ],
            "ValDtls": {
                "AssVal": 1600.0, "CgstVal": 78.1, "SgstVal": 78.1, "IgstVal": 0.0, "CesVal": 51.59,
                "StCesVal": 0.0, "Discount": 0.0, "RndOffAmt": 0.0, "TotInvVal": 1807.79
            },
        })
        self.assertDictEqual(json_value, expected, "Indian EDI with negative unit price sent json value is not matched")

        expected.update({"DocDtls": {"Typ": "INV", "No": "INV/18-19/0006", "Dt": "01/01/2019"}})
        json_value = self.env["account.edi.format"]._l10n_in_edi_generate_invoice_json(self.invoice_negative_qty)
        self.assertDictEqual(json_value, expected, "Indian EDI with negative quantity sent json value is not matched")

        expected.update({"DocDtls": {"Typ": "INV", "No": "INV/18-19/0007", "Dt": "01/01/2019"}})
        json_value = self.env["account.edi.format"]._l10n_in_edi_generate_invoice_json(self.invoice_negative_unit_price_and_qty)
        self.assertDictEqual(json_value, expected, "Indian EDI with negative unit price and quantity sent json value is not matched")

        expected.update({
            "DocDtls": {"Typ": "INV", "No": "INV/18-19/0008", "Dt": "01/01/2019"},
            "ItemList": [{
                "SlNo": "1", "PrdDesc": "product_a", "IsServc": "N", "HsnCd": "111111", "Qty": 1.0,
                "Unit": "UNT", "UnitPrice": 2000.0, "TotAmt": 2000.0, "Discount": 1400.0, "AssAmt": 600.0,
                "GstRt": 5.0, "IgstAmt": 0.0, "CgstAmt": 15.0, "SgstAmt": 15.0, "CesRt": 0.0, "CesAmt": 0.0,
                "CesNonAdvlAmt": 0.0, "StateCesRt": 0.0, "StateCesAmt": 0.0, "StateCesNonAdvlAmt": 0.0,
                "OthChrg": 0.0, "TotItemVal": 630.0
            }],
            "ValDtls": {
                "AssVal": 600.0, "CgstVal": 15.0, "SgstVal": 15.0, "IgstVal": 0.0, "CesVal": 0.0,
                "StCesVal": 0.0, "Discount": 0.0, "RndOffAmt": 0.0, "TotInvVal": 630.0
            },
        })
        json_value = self.env["account.edi.format"]._l10n_in_edi_generate_invoice_json(self.invoice_negative_with_discount)
        self.assertDictEqual(json_value, expected, "Indian EDI with negative unit price and quantity sent json value is not matched")

        expected.update({
            "DocDtls": {"Typ": "INV", "No": "INV/18-19/0009", "Dt": "01/01/2019"},
            "ItemList": [{
                "SlNo": "1", "PrdDesc": "product_a", "IsServc": "N", "HsnCd": "111111", "Qty": 1.0,
                "Unit": "UNT", "UnitPrice": 2000.0, "TotAmt": 2000.0, "Discount": 2000.0, "AssAmt": 0.0,
                "GstRt": 5.0, "IgstAmt": 0.0, "CgstAmt": 0.0, "SgstAmt": 0.0, "CesRt": 0.0, "CesAmt": 0.0,
                "CesNonAdvlAmt": 0.0, "StateCesRt": 0.0, "StateCesAmt": 0.0, "StateCesNonAdvlAmt": 0.0,
                "OthChrg": 0.0, "TotItemVal": 0.0
            },
            {
                "SlNo": "2", "PrdDesc": "product_b", "IsServc": "N", "HsnCd": "111111", "Qty": 1.0,
                "Unit": "UNT", "UnitPrice": 1000.0, "TotAmt": 1000.0, "Discount": 100.0, "AssAmt": 900.0,
                "GstRt": 5.0, "IgstAmt": 0.0, "CgstAmt": 22.5, "SgstAmt": 22.5, "CesRt": 0.0, "CesAmt": 0.0,
                "CesNonAdvlAmt": 0.0, "StateCesRt": 0.0, "StateCesAmt": 0.0, "StateCesNonAdvlAmt": 0.0,
                "OthChrg": 0.0, "TotItemVal": 945.0
            }],
            "ValDtls": {
                "AssVal": 900.0, "CgstVal": 22.5, "SgstVal": 22.5, "IgstVal": 0.0, "CesVal": 0.0,
                "StCesVal": 0.0, "Discount": 0.0, "RndOffAmt": 0.0, "TotInvVal": 945.0
            },
        })
        json_value = self.env['account.edi.format']._l10n_in_edi_generate_invoice_json(self.invoice_negative_more_than_max_line)
        self.assertDictEqual(json_value, expected, "Indian EDI with negative value more than max line sent json value is not matched")

        json_value = self.env["account.edi.format"]._l10n_in_edi_generate_invoice_json(self.invoice_cash_rounding)
        expected_copy_rounding.update({
            "DocDtls": {"Typ": "INV", "No": "INV/18-19/0010", "Dt": "01/01/2019"},
            "ValDtls": {
                "AssVal": 1800.0, "CgstVal": 79.3, "SgstVal": 79.3, "IgstVal": 0.0, "CesVal": 46.59,
                "StCesVal": 0.0, "Discount": 0.0, "RndOffAmt": -0.19, "TotInvVal": 2005.00
            }})
        self.assertDictEqual(json_value, expected_copy_rounding, "Indian EDI with cash rounding sent json value is not matched")
