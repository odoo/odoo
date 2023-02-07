# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo import Command


@tagged("post_install_l10n", "post_install", "-at_install")
class TestEdiJson(AccountTestInvoicingCommon):


    @classmethod
    def setUpClass(cls, chart_template_ref="l10n_in.indian_chart_template_standard"):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.env['ir.config_parameter'].set_param('l10n_in_edi.manage_invoice_negative_lines', True)
        cls.maxDiff = None
        cls.company_data["company"].write({
            "street": "Block no. 401",
            "street2": "Street 2",
            "city": "City 1",
            "zip": "500001",
            "state_id": cls.env.ref("base.state_in_ts").id,
            "country_id": cls.env.ref("base.in").id,
            "vat": "36AABCT1332L011",
        })
        cls.partner_a.write({
            "vat": "36BBBFF5679L8ZR",
            "street": "Block no. 401",
            "street2": "Street 2",
            "city": "City 2",
            "zip": "500001",
            "state_id": cls.env.ref("base.state_in_ts").id,
            "country_id": cls.env.ref("base.in").id,
            "l10n_in_gst_treatment": "regular",
        })
        cls.product_a.write({"l10n_in_hsn_code": "01111"})
        cls.product_a2 = cls.env['product.product'].create({
            'name': 'product_a2',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'lst_price': 1000.0,
            'standard_price': 1000.0,
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
            'property_account_expense_id': cls.company_data['default_account_expense'].id,
            'taxes_id': [(6, 0, cls.tax_sale_a.ids)],
            'supplier_taxes_id': [(6, 0, cls.tax_purchase_a.ids)],
            "l10n_in_hsn_code": "01111",
        })
        cls.product_a_discount = cls.env['product.product'].create({
            'name': 'product_a discount',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'lst_price': 400.0,
            'standard_price': 400.0,
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
            'property_account_expense_id': cls.company_data['default_account_expense'].id,
            'taxes_id': [(6, 0, cls.tax_sale_a.ids)],
            'supplier_taxes_id': [(6, 0, cls.tax_purchase_a.ids)],
            "l10n_in_hsn_code": "01111",
        })
        gst_with_cess = cls.env.ref("l10n_in.%s_sgst_sale_12" % (cls.company_data["company"].id)
            ) + cls.env.ref("l10n_in.%s_cess_5_plus_1591_sale" % (cls.company_data["company"].id))
        product_with_cess = cls.env["product.product"].create({
            "name": "product_with_cess",
            "uom_id": cls.env.ref("uom.product_uom_unit").id,
            "lst_price": 1000.0,
            "standard_price": 800.0,
            "property_account_income_id": cls.company_data["default_account_revenue"].id,
            "property_account_expense_id": cls.company_data["default_account_expense"].id,
            "taxes_id": [(6, 0, gst_with_cess.ids)],
            "supplier_taxes_id": [(6, 0, cls.tax_purchase_a.ids)],
            "l10n_in_hsn_code": "02222",
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
        cls.invoice_negative_more_than_max_line = cls.init_invoice("out_invoice", post=False, products=cls.product_a + cls.product_a2 + cls.product_a_discount)
        cls.invoice_negative_more_than_max_line.write({
            "invoice_line_ids": [
                (1, cls.invoice_negative_more_than_max_line.invoice_line_ids[0].id, {"price_unit": 2000, 'discount': 50}),
                (1, cls.invoice_negative_more_than_max_line.invoice_line_ids[1].id, {"price_unit": 1000}),
                (1, cls.invoice_negative_more_than_max_line.invoice_line_ids[2].id, {"price_unit": -1100}),
            ]})
        cls.invoice_negative_more_than_max_line.action_post()

    def test_edi_json(self):
        json_value = self.env["account.edi.format"]._l10n_in_edi_generate_invoice_json(self.invoice)
        expected = {
            "Version": "1.1",
            "TranDtls": {"TaxSch": "GST", "SupTyp": "B2B", "RegRev": "N", "IgstOnIntra": "N"},
            "DocDtls": {"Typ": "INV", "No": "INV/2019/00001", "Dt": "01/01/2019"},
            "SellerDtls": {
                "LglNm": "company_1_data",
                "Addr1": "Block no. 401",
                "Addr2": "Street 2",
                "Loc": "City 1",
                "Pin": 500001,
                "Stcd": "36",
                "GSTIN": "36AABCT1332L011"},
            "BuyerDtls": {
                "LglNm": "partner_a",
                "Addr1": "Block no. 401",
                "Addr2": "Street 2",
                "Loc": "City 2",
                "Pin": 500001,
                "Stcd": "36",
                "POS": "36",
                "GSTIN": "36BBBFF5679L8ZR"},
            "ItemList": [
                {
                    "SlNo": "1", "PrdDesc": "product_a", "IsServc": "N", "HsnCd": "01111", "Qty": 1.0,
                    "Unit": "UNT", "UnitPrice": 1000.0, "TotAmt": 1000.0, "Discount": 100.0, "AssAmt": 900.0,
                    "GstRt": 5.0, "IgstAmt": 0.0, "CgstAmt": 22.5, "SgstAmt": 22.5, "CesRt": 0.0, "CesAmt": 0.0,
                    "CesNonAdvlAmt": 0.0, "StateCesRt": 0.0, "StateCesAmt": 0.0, "StateCesNonAdvlAmt": 0.0,
                    "OthChrg": 0.0, "TotItemVal": 945.0
                },
                {
                    "SlNo": "2", "PrdDesc": "product_with_cess", "IsServc": "N", "HsnCd": "02222", "Qty": 1.0,
                    "Unit": "UNT", "UnitPrice": 1000.0, "TotAmt": 1000.0, "Discount": 100.0, "AssAmt": 900.0,
                    "GstRt": 12.0, "IgstAmt": 0.0, "CgstAmt": 54.0, "SgstAmt": 54.0, "CesRt": 5.0, "CesAmt": 45.0,
                    "CesNonAdvlAmt": 1.59, "StateCesRt": 0.0, "StateCesAmt": 0.0, "StateCesNonAdvlAmt": 0.0,
                    "OthChrg": 0.0, "TotItemVal": 1054.59
                }
            ],
            "ValDtls": {
                "AssVal": 1800.0, "CgstVal": 76.5, "SgstVal": 76.5, "IgstVal": 0.0, "CesVal": 46.59,
                "StCesVal": 0.0, "RndOffAmt": 0.0, "TotInvVal": 1999.59
            }
        }
        self.assertDictEqual(json_value, expected, "Indian EDI send json value is not matched")

        #=================================== Full discount test =====================================
        json_value = self.env["account.edi.format"]._l10n_in_edi_generate_invoice_json(self.invoice_full_discount)
        expected.update({
            "DocDtls": {"Typ": "INV", "No": "INV/2019/00002", "Dt": "01/01/2019"},
            "ItemList": [{
                "SlNo": "1", "PrdDesc": "product_a", "IsServc": "N", "HsnCd": "01111", "Qty": 1.0,
                "Unit": "UNT", "UnitPrice": 1000.0, "TotAmt": 1000.0, "Discount": 1000.0, "AssAmt": 0.0,
                "GstRt": 0.0, "IgstAmt": 0.0, "CgstAmt": 0.0, "SgstAmt": 0.0, "CesRt": 0.0, "CesAmt": 0.0,
                "CesNonAdvlAmt": 0.0, "StateCesRt": 0.0, "StateCesAmt": 0.0, "StateCesNonAdvlAmt": 0.0,
                "OthChrg": 0.0, "TotItemVal": 0.0}],
            "ValDtls": {"AssVal": 0.0, "CgstVal": 0.0, "SgstVal": 0.0, "IgstVal": 0.0, "CesVal": 0.0,
                "StCesVal": 0.0, "RndOffAmt": 0.0, "TotInvVal": 0.0}
        })
        self.assertDictEqual(json_value, expected, "Indian EDI with 100% discount sent json value is not matched")

        #=================================== Zero quantity test =============================================
        json_value = self.env["account.edi.format"]._l10n_in_edi_generate_invoice_json(self.invoice_zero_qty)
        expected.update({
            "DocDtls": {"Typ": "INV", "No": "INV/2019/00003", "Dt": "01/01/2019"},
            "ItemList": [{
                "SlNo": "1", "PrdDesc": "product_a", "IsServc": "N", "HsnCd": "01111", "Qty": 0.0,
                "Unit": "UNT", "UnitPrice": 1000.0, "TotAmt": 0.0, "Discount": 0.0, "AssAmt": 0.0,
                "GstRt": 0.0, "IgstAmt": 0.0, "CgstAmt": 0.0, "SgstAmt": 0.0, "CesRt": 0.0, "CesAmt": 0.0,
                "CesNonAdvlAmt": 0.0, "StateCesRt": 0.0, "StateCesAmt": 0.0, "StateCesNonAdvlAmt": 0.0,
                "OthChrg": 0.0, "TotItemVal": 0.0}],
        })
        self.assertDictEqual(json_value, expected, "Indian EDI with 0(zero) quantity sent json value is not matched")

        #=================================== Negative unit price test =============================================
        json_value = self.env["account.edi.format"]._l10n_in_edi_generate_invoice_json(self.invoice_negative_unit_price)
        expected.update({
            "DocDtls": {"Typ": "INV", "No": "INV/2019/00004", "Dt": "01/01/2019"},
            "ItemList": [
                {
                    "SlNo": "1", "PrdDesc": "product_a", "IsServc": "N", "HsnCd": "01111", "Qty": 1.0,
                    "Unit": "UNT", "UnitPrice": 1000.0, "TotAmt": 1000.0, "Discount": 400.0, "AssAmt": 600.0,
                    "GstRt": 5.0, "IgstAmt": 0.0, "CgstAmt": 15.0, "SgstAmt": 15.0, "CesRt": 0.0, "CesAmt": 0.0,
                    "CesNonAdvlAmt": 0.0, "StateCesRt": 0.0, "StateCesAmt": 0.0, "StateCesNonAdvlAmt": 0.0,
                    "OthChrg": 0.0, "TotItemVal": 630.0
                },
                {
                    "SlNo": "3", "PrdDesc": "product_with_cess", "IsServc": "N", "HsnCd": "02222", "Qty": 1.0,
                    "Unit": "UNT", "UnitPrice": 1000.0, "TotAmt": 1000.0, "Discount": 0.0, "AssAmt": 1000.0,
                    "GstRt": 12.0, "IgstAmt": 0.0, "CgstAmt": 60.0, "SgstAmt": 60.0, "CesRt": 5.0, "CesAmt": 50.0,
                    "CesNonAdvlAmt": 1.59, "StateCesRt": 0.0, "StateCesAmt": 0.0, "StateCesNonAdvlAmt": 0.0,
                    "OthChrg": 0.0, "TotItemVal": 1171.59
                }
            ],
            "ValDtls": {
                "AssVal": 1600.0, "CgstVal": 75.0, "SgstVal": 75.0, "IgstVal": 0.0, "CesVal": 51.59,
                "StCesVal": 0.0, "RndOffAmt": 0.0, "TotInvVal": 1801.59
            },
        })
        self.assertDictEqual(json_value, expected, "Indian EDI with negative unit price sent json value is not matched")

        expected.update({"DocDtls": {"Typ": "INV", "No": "INV/2019/00005", "Dt": "01/01/2019"}})
        json_value = self.env["account.edi.format"]._l10n_in_edi_generate_invoice_json(self.invoice_negative_qty)
        self.assertDictEqual(json_value, expected, "Indian EDI with negative quantity sent json value is not matched")

        expected.update({"DocDtls": {"Typ": "INV", "No": "INV/2019/00006", "Dt": "01/01/2019"}})
        json_value = self.env["account.edi.format"]._l10n_in_edi_generate_invoice_json(self.invoice_negative_unit_price_and_qty)
        self.assertDictEqual(json_value, expected, "Indian EDI with negative unit price and quantity sent json value is not matched")

        expected.update({
            "DocDtls": {"Typ": "INV", "No": "INV/2019/00007", "Dt": "01/01/2019"},
            "ItemList": [{
                "SlNo": "1", "PrdDesc": "product_a", "IsServc": "N", "HsnCd": "01111", "Qty": 1.0,
                "Unit": "UNT", "UnitPrice": 2000.0, "TotAmt": 2000.0, "Discount": 1400.0, "AssAmt": 600.0,
                "GstRt": 5.0, "IgstAmt": 0.0, "CgstAmt": 15.0, "SgstAmt": 15.0, "CesRt": 0.0, "CesAmt": 0.0,
                "CesNonAdvlAmt": 0.0, "StateCesRt": 0.0, "StateCesAmt": 0.0, "StateCesNonAdvlAmt": 0.0,
                "OthChrg": 0.0, "TotItemVal": 630.0
            }],
            "ValDtls": {
                "AssVal": 600.0, "CgstVal": 15.0, "SgstVal": 15.0, "IgstVal": 0.0, "CesVal": 0.0,
                "StCesVal": 0.0, "RndOffAmt": 0.0, "TotInvVal": 630.0
            },
        })
        json_value = self.env["account.edi.format"]._l10n_in_edi_generate_invoice_json(self.invoice_negative_with_discount)
        self.assertDictEqual(json_value, expected, "Indian EDI with negative unit price and quantity sent json value is not matched")

        expected.update({
            "DocDtls": {"Typ": "INV", "No": "INV/2019/00008", "Dt": "01/01/2019"},
            "ItemList": [{
                "SlNo": "1", "PrdDesc": "product_a", "IsServc": "N", "HsnCd": "01111", "Qty": 1.0,
                "Unit": "UNT", "UnitPrice": 2000.0, "TotAmt": 2000.0, "Discount": 2000.0, "AssAmt": 0.0,
                "GstRt": 5.0, "IgstAmt": 0.0, "CgstAmt": 0.0, "SgstAmt": 0.0, "CesRt": 0.0, "CesAmt": 0.0,
                "CesNonAdvlAmt": 0.0, "StateCesRt": 0.0, "StateCesAmt": 0.0, "StateCesNonAdvlAmt": 0.0,
                "OthChrg": 0.0, "TotItemVal": 0.0
            },
            {
                "SlNo": "2", "PrdDesc": "product_a2", "IsServc": "N", "HsnCd": "01111", "Qty": 1.0,
                "Unit": "UNT", "UnitPrice": 1000.0, "TotAmt": 1000.0, "Discount": 100.0, "AssAmt": 900.0,
                "GstRt": 5.0, "IgstAmt": 0.0, "CgstAmt": 22.5, "SgstAmt": 22.5, "CesRt": 0.0, "CesAmt": 0.0,
                "CesNonAdvlAmt": 0.0, "StateCesRt": 0.0, "StateCesAmt": 0.0, "StateCesNonAdvlAmt": 0.0,
                "OthChrg": 0.0, "TotItemVal": 945.0
            }],
            "ValDtls": {
                "AssVal": 900.0, "CgstVal": 22.5, "SgstVal": 22.5, "IgstVal": 0.0, "CesVal": 0.0,
                "StCesVal": 0.0, "RndOffAmt": 0.0, "TotInvVal": 945.0
            },
        })
        json_value = self.env['account.edi.format']._l10n_in_edi_generate_invoice_json(self.invoice_negative_more_than_max_line)
        self.assertDictEqual(json_value, expected, "Indian EDI with negative value more than max line sent json value is not matched")

    def test_edi_json_equal_sgst_cgst(self):
        """
            In price include tax some time we have issue where sgst cgst tax amount is not equal
            So we create rounding tax with 0.01
        """
        round_off_tax = self.env['account.tax'].create({
            'name': 'Round Off',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 0.01,
            'invoice_repartition_line_ids': [
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'base',
                }),
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'tag_ids': [(6, 0, self.env.ref("l10n_in.tax_tag_round_off").ids)],
                }),
            ],
            'refund_repartition_line_ids': [
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'base',
                }),
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'tag_ids': [(6, 0, self.env.ref("l10n_in.tax_tag_round_off").ids)],
                }),
            ],
        })
        gst_5 = self.env.ref("l10n_in.%s_sgst_sale_5" % (self.company_data["company"].id))
        gst_5.write({
            'children_tax_ids': [(4, round_off_tax.id)],
        })
        gst_5.children_tax_ids.write({
            'price_include' : True,
            'include_base_amount': False
        })
        invoice_2 = self.init_invoice("out_invoice", post=False, products=self.product_a, taxes=gst_5)
        invoice_2.write({"invoice_line_ids": [(1, invoice_2.invoice_line_ids[0].id, {"price_unit": 100})]})
        invoice_2.action_post()
        json_value = self.env["account.edi.format"]._l10n_in_edi_generate_invoice_json(invoice_2)
        expected = {
            "Version": "1.1", "TranDtls": {"TaxSch": "GST", "SupTyp": "B2B", "RegRev": "N", "IgstOnIntra": "N"},
            "DocDtls": {"Typ": "INV", "No": "INV/2019/00009", "Dt": "01/01/2019"},
            "SellerDtls": {
                "Addr1": "Block no. 401", "Loc": "City 1", "Pin": 500001, "Stcd": "36", "Addr2": "Street 2",
                "LglNm": "company_1_data", "GSTIN": "36AABCT1332L011"
            },
            "BuyerDtls": {"Addr1": "Block no. 401", "Loc": "City 2", "Pin": 500001, "Stcd": "36", "Addr2": "Street 2", "POS": "36", "LglNm": "partner_a", "GSTIN": "36BBBFF5679L8ZR"},
            "ItemList": [{
                "SlNo": "1", "PrdDesc": "product_a", "IsServc": "N", "HsnCd": "01111", "Qty": 1.0,
                "Unit": "UNT", "UnitPrice": 95.23, "TotAmt": 95.23, "Discount": 0.0, "AssAmt": 95.23,
                "GstRt": 5.0, "IgstAmt": 0.0, "CgstAmt": 2.38, "SgstAmt": 2.38, "CesRt": 0.0, "CesAmt": 0.0,
                "CesNonAdvlAmt": 0.0, "StateCesRt": 0.0, "StateCesAmt": 0.0, "StateCesNonAdvlAmt": 0.0,
                "OthChrg": 0.0, "TotItemVal": 100.0
            }],
            "ValDtls": {
                "AssVal": 95.23, "CgstVal": 2.38, "SgstVal": 2.38, "IgstVal": 0.0, "CesVal": 0.0,
                "StCesVal": 0.0, "RndOffAmt": 0.01, "TotInvVal": 100.0
            }
        }
        self.assertDictEqual(json_value, expected, "Indian EDI send json with equlal CGST and SGST value is not matched!")
