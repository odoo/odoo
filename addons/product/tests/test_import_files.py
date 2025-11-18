# Part of Odoo. See LICENSE file for full copyright and licensing details.

import unittest

from odoo.tests import TransactionCase, can_import, loaded_demo_data, tagged
from odoo.tools import mute_logger
from odoo.tools.misc import file_open


@tagged("post_install", "-at_install")
class TestImportFiles(TransactionCase):

    def import_product_xls(self, model, filepath=None):
        if filepath is None:
            filepath = f"product/static/xls/{model.replace(".", "_")}.xls"
        file_content = file_open(filepath, "rb").read()
        import_wizard = self.env["base_import.import"].create(
            {
                "res_model": model,
                "file": file_content,
                "file_type": "application/vnd.ms-excel",
            }
        )

        result = import_wizard.parse_preview(
            {
                "has_headers": True,
            }
        )
        self.assertIsNone(result.get("error"))
        field_names = ['/'.join(v) for v in result["matches"].values()]
        results = import_wizard.execute_import(
            field_names,
            [r.lower() for r in result["headers"]],
            {
                "import_skip_records": [],
                "import_set_empty_fields": [],
                "fallback_values": {},
                "name_create_enabled_fields": {},
                "encoding": "",
                "separator": "",
                "quoting": '"',
                "date_format": "",
                "datetime_format": "",
                "float_thousand_separator": ",",
                "float_decimal_separator": ".",
                "advanced": True,
                "has_headers": True,
                "keep_matches": False,
                "limit": 2000,
                "skip": 0,
                "tracking_disable": True,
            },
        )
        return results

    @unittest.skipUnless(
        can_import("xlrd.xlsx") or can_import("openpyxl"), "XLRD/XLSX not available"
    )
    def test_import_create_product_demo_xls(self):
        if not loaded_demo_data(self.env):
            self.skipTest('Needs demo data to be able to import those files')

        for model in ("product.pricelist", "product.supplierinfo", "product.template"):
            with self.subTest(model):
                results = self.import_product_xls(model)
                self.assertFalse(
                    results["messages"],
                    "results should be empty on successful import of ",
                )

        with self.subTest("product.product"):
            results = self.import_product_xls("product.product")
            results = self.assertFalse(
                results["messages"],
                "results should be empty on successful import of ",
            )

            template = self.env.ref('__import__.product_template_BB')
            self.assertEqual(self.env.ref('__import__.product_product_1').list_price, 110)
            self.assertEqual(len(template.product_variant_ids), 8)
            self.assertEqual([
                p.import_attribute_values
                for p in template.product_variant_ids
            ], [
                'Color:Red,Size:S',
                'Color:Red,Size:M',
                'Color:Red,Size:L',
                'Color:Blue,Size:XL',
                'Color:Blue,Size:S',
                'Color:Blue,Size:M',
                'Color:Blue,Size:L',
                'Color:Red,Size:XL'
            ])

    def test_import_write_product_demo_xls(self):
        self.import_product_xls("product.product")  # create products
        template = self.env.ref('__import__.product_template_BB')
        self.assertEqual(len(template.product_variant_ids), 8)
        self.assertEqual(self.env.ref('__import__.product_product_1').standard_price, 40)
        self.assertEqual(self.env.ref('__import__.product_tshirt_SW_red_m').standard_price, 45)
        self.assertEqual(self.env.ref('__import__.product_tshirt_SW_red_l').standard_price, 50)
        self.assertEqual(self.env.ref('__import__.product_tshirt_SW_blue_xl').standard_price, 55)
        self.assertEqual(self.env.ref('__import__.product_product_1').lst_price, 110)
        self.assertEqual(self.env.ref('__import__.product_product_6').lst_price, 110)
        # self.assertEqual(self.env.ref('__import__.product_tshirt_SW_red_l').lst_price, 0)  # TODO: the price can be imported for each product regardless of others

        self.import_product_xls("product.product", filepath="product/static/xls/test_import_update_product_price.xls")  # update products

        self.assertEqual(len(template.product_variant_ids), 8)

        self.assertEqual(self.env.ref('__import__.product_product_1').standard_price, 1000)
        self.assertEqual(self.env.ref('__import__.product_product_2').standard_price, 40)
        self.assertEqual(self.env.ref('__import__.product_product_6').standard_price, 1001)
        self.assertEqual(self.env.ref('__import__.product_tshirt_SW_red_m').standard_price, 45)
        self.assertEqual(self.env.ref('__import__.product_tshirt_SW_red_l').standard_price, 1002)
        self.assertEqual(self.env.ref('__import__.product_tshirt_SW_blue_xl').standard_price, 55)
        # self.assertEqual(self.env.ref('__import__.product_product_1').lst_price, 2000)  # TODO: the price can be imported for each product regardless of others
        self.assertEqual(self.env.ref('__import__.product_product_6').lst_price, 2001)
        self.assertEqual(self.env.ref('__import__.product_tshirt_SW_red_l').lst_price, 2002)

    @mute_logger('odoo.sql_db')
    def test_import_write_product_xls_error(self):
        results = self.import_product_xls("product.product")  # create products
        self.assertFalse(
            results["messages"],
            "results should be empty on successful import of ",
        )

        results = self.import_product_xls("product.product", filepath="product/static/xls/test_import_update_error.xls")  # update products
        self.assertIn(
            'The exitings product has different attribute value. "Color:Yellow,Size:M" is not equivalent to "Color:Blue,Size:M" for "__import__.product_product_6"',
            results["messages"][0]["message"])
        self.assertIn(
            'The exitings product has different attribute value. "Color:Black,Size:L" is not equivalent to "Color:Red,Size:L" for "__import__.product_tshirt_SW_red_l"',
            results["messages"][-1]["message"])

        results = self.import_product_xls("product.product", filepath="product/static/xls/test_import_update_error_2.xls")  # update products
        self.assertIn('already exists', results["messages"][0]["message"])

    def test_import_product_without_values_xls(self):
        # Some field must be imported only once and only on product.product like
        # qty_available. If the field is imported when we create the
        # product.template the quantity should be add on the the default first
        # product.product. But the product should be removed after import some
        # variant.

        addons = tuple(self.env.registry._init_modules) + (self.env.context.get('install_module'),)
        if 'stock' not in addons:
            self.skipTest('Needs stock addon for this test')
            return

        self.import_product_xls("product.product", filepath="product/static/xls/test_import_product_without_values.xls")

        self.assertEqual(self.env.ref('__import__.product_template_1').qty_available, 3.0)
        self.assertEqual(self.env.ref('__import__.product_product_1').qty_available, 100.0)

    def test_import_create_product_template_xls(self):
        results = self.import_product_xls("product.template", filepath="product/static/xls/test_import_template.xls")

        self.assertFalse(results["messages"])

        product = self.env['product.product'].search([('default_code', '=', 'CERT20')])
        self.assertEqual(product.list_price, 200)
        self.assertEqual(product.standard_price, 5)
