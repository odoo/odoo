# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestTileFunctions(TransactionCase):
    """Test aggregation functions: count, sum, min, max, avg, median."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model_id = cls.env["ir.model"].search(
            [("model", "=", "tile.tile")], limit=1,
        )
        cls.category = cls.env.ref("web_dashboard_tile.category_module")
        cls.field_id = cls.env["ir.model.fields"].search(
            [("model_id", "=", cls.model_id.id), ("name", "=", "sequence")],
            limit=1,
        )

    def _create_tile(self, vals):
        defaults = {
            "category_id": self.category.id,
            "model_id": self.model_id.id,
            "domain": "[('model_id', '=', %d)]" % self.model_id.id,
        }
        defaults.update(vals)
        return self.env["tile.tile"].create(defaults)

    def test_count_and_sum(self):
        tile = self._create_tile({
            "name": "Count / Sum",
            "sequence": 1,
            "secondary_function": "sum",
            "secondary_field_id": self.field_id.id,
        })
        self.assertEqual(tile.primary_value, 1.0)
        self.assertIsInstance(tile.primary_formated_value, str)

    def test_min_max(self):
        tile = self._create_tile({
            "name": "Min / Max",
            "sequence": 2,
            "primary_function": "min",
            "primary_field_id": self.field_id.id,
            "secondary_function": "max",
            "secondary_field_id": self.field_id.id,
        })
        self.assertGreaterEqual(tile.secondary_value, tile.primary_value)

    def test_avg_median(self):
        tile = self._create_tile({
            "name": "Avg / Median",
            "sequence": 3,
            "primary_function": "avg",
            "primary_field_id": self.field_id.id,
            "secondary_function": "median",
            "secondary_field_id": self.field_id.id,
        })
        self.assertIsInstance(tile.primary_value, float)
        self.assertIsInstance(tile.secondary_value, float)


class TestTileEdgeCases(TransactionCase):
    """Test error handling and edge cases."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model_id = cls.env["ir.model"].search(
            [("model", "=", "tile.tile")], limit=1,
        )
        cls.category = cls.env.ref("web_dashboard_tile.category_module")

    def test_invalid_domain(self):
        tile = self.env["tile.tile"].create({
            "name": "Bad Domain",
            "category_id": self.category.id,
            "model_id": self.model_id.id,
            "domain": "[('INVALID",
        })
        self.assertTrue(tile.domain_error)
        self.assertEqual(tile.primary_formated_value, "Domain Error")

    def test_empty_domain(self):
        tile = self.env["tile.tile"].create({
            "name": "Empty",
            "category_id": self.category.id,
            "model_id": self.model_id.id,
            "domain": "[]",
        })
        self.assertFalse(tile.domain_error)
        self.assertGreaterEqual(tile.primary_value, 0)

    def test_hide_if_null(self):
        tile = self.env["tile.tile"].create({
            "name": "Hidden",
            "category_id": self.category.id,
            "model_id": self.model_id.id,
            "domain": "[('id', '=', -1)]",
            "hide_if_null": True,
        })
        self.assertTrue(tile.hidden)

    def test_invalid_format_string(self):
        tile = self.env["tile.tile"].create({
            "name": "Bad Format",
            "category_id": self.category.id,
            "model_id": self.model_id.id,
            "domain": "[]",
            "primary_format": "{invalid",
        })
        self.assertTrue(tile.primary_error)

    def test_open_link_returns_action(self):
        tile = self.env["tile.tile"].create({
            "name": "Link Test",
            "category_id": self.category.id,
            "model_id": self.model_id.id,
            "domain": "[]",
        })
        action = tile.open_link()
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertIsInstance(action["domain"], list)

    def test_open_link_bad_domain_fallback(self):
        tile = self.env["tile.tile"].create({
            "name": "Bad Link",
            "category_id": self.category.id,
            "model_id": self.model_id.id,
            "domain": "[BROKEN",
        })
        action = tile.open_link()
        self.assertEqual(action["domain"], [])


class TestTileColorValidation(TransactionCase):
    """Test CSS injection prevention."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model_id = cls.env["ir.model"].search(
            [("model", "=", "tile.tile")], limit=1,
        )
        cls.category = cls.env.ref("web_dashboard_tile.category_module")

    def test_valid_hex_color(self):
        tile = self.env["tile.tile"].create({
            "name": "Valid Color",
            "category_id": self.category.id,
            "model_id": self.model_id.id,
            "background_color": "#FF5733",
            "font_color": "#FFFFFF",
        })
        self.assertEqual(tile.background_color, "#FF5733")

    def test_invalid_color_rejected(self):
        with self.assertRaises(ValidationError):
            self.env["tile.tile"].create({
                "name": "CSS Injection",
                "category_id": self.category.id,
                "model_id": self.model_id.id,
                "background_color": "#FFF; position:fixed",
            })

    def test_invalid_short_hex_rejected(self):
        with self.assertRaises(ValidationError):
            self.env["tile.tile"].create({
                "name": "Short Hex",
                "category_id": self.category.id,
                "model_id": self.model_id.id,
                "background_color": "#FFF",
            })


class TestTileCategory(TransactionCase):
    """Test category CRUD and UI management."""

    def test_create_category_creates_menu(self):
        cat = self.env["tile.category"].create({
            "name": "Test Category",
            "sequence": 99,
        })
        self.assertTrue(cat.action_id)
        self.assertTrue(cat.menu_id)

    def test_archive_category_removes_menu(self):
        cat = self.env["tile.category"].create({
            "name": "Archive Test",
            "sequence": 99,
        })
        menu_id = cat.menu_id.id
        cat.write({"active": False})
        self.assertFalse(
            self.env["ir.ui.menu"].search([("id", "=", menu_id)]),
        )

    def test_delete_category_cleans_up(self):
        cat = self.env["tile.category"].create({
            "name": "Delete Test",
            "sequence": 99,
        })
        action_id = cat.action_id.id
        menu_id = cat.menu_id.id
        cat.unlink()
        self.assertFalse(
            self.env["ir.actions.act_window"].search(
                [("id", "=", action_id)],
            ),
        )
        self.assertFalse(
            self.env["ir.ui.menu"].search([("id", "=", menu_id)]),
        )
