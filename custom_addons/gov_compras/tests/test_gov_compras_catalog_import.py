import base64

from odoo.tests import common


class TestGovComprasCatalogImport(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.Category = self.env["gov.compras.category"]
        self.Item = self.env["gov.compras.catalog.item"]
        self.Wizard = self.env["gov.compras.import.wizard"]
        self.uom_unit = self.env.ref("uom.product_uom_unit")
        self.natureza = self.env["gov.account.config"].search(
            [("natureza_despesa", "=", "3.3.90.30")],
            limit=1,
        )

    def test_category_hierarchy_generates_internal_codes(self):
        root_a = self.Category.create({"name": "Material"})
        root_b = self.Category.create({"name": "Serviços"})
        child = self.Category.create(
            {
                "name": "Papelaria",
                "parent_id": root_a.id,
            }
        )
        grandchild = self.Category.create(
            {
                "name": "Resmas",
                "parent_id": child.id,
            }
        )

        self.assertEqual(root_a.code, "01")
        self.assertEqual(root_b.code, "02")
        self.assertEqual(child.code, "01.01")
        self.assertEqual(grandchild.code, "01.01.01")

        child.write({"parent_id": root_b.id})

        self.assertEqual(child.code, "02.01")
        self.assertEqual(grandchild.code, "02.01.01")

    def test_import_uses_external_id_and_generates_internal_item_code(self):
        self.assertTrue(self.natureza)

        legacy_item = self.Item.create(
            {
                "name": "Item legado",
                "code": "EXT-001",
                "uom_id": self.uom_unit.id,
                "natureza_despesa_id": self.natureza.id,
            }
        )

        csv_content = (
            "Código;Nome do Item;Natureza da Despesa;Categoria;Subcategoria;Unidade de Medida;Descrição Técnica\n"
            "EXT-001;Papel A4;3.3.90.30;Material de Expediente;Papelaria;Unidade;Resma de papel A4\n"
            "EXT-002;Caneta Azul;3.3.90.30;Material de Expediente;Papelaria;Unidade;Caneta esferográfica azul\n"
        )
        wizard = self.Wizard.create(
            {
                "delimiter": ";",
                "filename": "catalogo.csv",
                "file": base64.b64encode(csv_content.encode("utf-8")).decode("ascii"),
            }
        )

        result = wizard.action_import()
        legacy_item = self.Item.browse(legacy_item.id)

        new_item = self.Item.search([("external_code", "=", "EXT-002")], limit=1)
        root_category = self.Category.search(
            [("name", "=", "Material de Expediente"), ("parent_id", "=", False)],
            limit=1,
        )
        subcategory = self.Category.search(
            [("name", "=", "Papelaria"), ("parent_id", "=", root_category.id)],
            limit=1,
        )

        self.assertEqual(result["params"]["type"], "success")
        self.assertTrue(root_category)
        self.assertTrue(subcategory)
        self.assertEqual(legacy_item.external_code, "EXT-001")
        self.assertEqual(legacy_item.name, "Papel A4")
        self.assertEqual(legacy_item.code, "EXT-001")
        self.assertTrue(new_item)
        self.assertEqual(new_item.external_code, "EXT-002")
        self.assertNotEqual(new_item.code, "EXT-002")
        self.assertTrue(new_item.code.startswith("ITM/"))
        self.assertEqual(root_category.code, "01")
        self.assertEqual(subcategory.code, "01.01")
        self.assertEqual(new_item.category_id, subcategory)
