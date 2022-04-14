# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install_l10n", "post_install", "-at_install")
class TestEdiJson(AccountTestInvoicingCommon):


    @classmethod
    def setUpClass(cls, chart_template_ref="l10n_in.indian_chart_template_standard"):
        super().setUpClass(chart_template_ref=chart_template_ref)
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
