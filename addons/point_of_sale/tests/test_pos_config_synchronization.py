import logging
from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.common import TestPoSCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestPosConfigSynchronization(TestPoSCommon):
    def _create_sync_order(self):
        session = self.env["pos.session"].create({"config_id": self.basic_config.id})
        product = self.env["product.product"].create(
            {"name": "Sync product", "available_in_pos": True}
        )
        return self.env["pos.order"].create(
            {
                "session_id": session.id,
                "company_id": self.basic_config.company_id.id,
                "amount_total": 10,
                "amount_paid": 0,
                "amount_tax": 0,
                "amount_return": 0,
                "lines": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "qty": 1,
                            "price_unit": 10,
                            "price_subtotal": 10,
                            "price_subtotal_incl": 10,
                        }
                    )
                ],
            }
        )

    def test_removed_lines_are_reported_without_a_line_search_domain(self):
        order = self._create_sync_order()
        line_ids = order.lines.ids
        order.lines.unlink()
        result = self.basic_config.read_config_open_orders(
            {"pos.order": [("id", "=", order.id)]},
            {"pos.order": order.ids, "pos.order.line": line_ids},
        )
        _logger.debug("Removed line synchronization: %s", result["deleted_record_ids"])
        self.assertEqual(result["deleted_record_ids"].get("pos.order.line"), line_ids)

    def test_order_payload_extensions_are_preserved(self):
        order = self._create_sync_order()
        Order = type(order)
        original = Order.read_pos_data

        def read_extended_data(records, data, config):
            result = original(records, data, config)
            for row in result["pos.order"]:
                row["extension_value"] = "retained"
            return result

        with patch.object(Order, "read_pos_data", read_extended_data):
            result = self.basic_config.read_config_open_orders(
                {"pos.order": [("id", "=", order.id)]}
            )
        _logger.debug(
            "Synchronized order keys: %s",
            result["dynamic_records"]["pos.order"][0].keys(),
        )
        self.assertEqual(
            result["dynamic_records"]["pos.order"][0].get("extension_value"), "retained"
        )

    def test_domain_results_keep_the_model_order(self):
        order = self._create_sync_order()
        other = order.copy({"name": "Newer order"})
        domain = [("id", "in", (order | other).ids)]
        expected = self.env["pos.order"].search(domain).ids
        result = self.basic_config.read_config_open_orders({"pos.order": domain})
        actual = [row["id"] for row in result["dynamic_records"]["pos.order"]]
        _logger.debug(
            "Synchronized order ordering: expected=%s actual=%s", expected, actual
        )
        self.assertEqual(actual, expected)

    def test_explicit_line_domain_merges_related_and_additional_lines(self):
        order = self._create_sync_order()
        other = order.copy({"name": "Additional lines"})
        result = self.basic_config.read_config_open_orders(
            {
                "pos.order": [("id", "=", order.id)],
                "pos.order.line": [("id", "in", other.lines.ids)],
            }
        )
        ids = [row["id"] for row in result["dynamic_records"]["pos.order.line"]]
        _logger.debug("Merged line domains: %s", ids)
        self.assertEqual(ids, (other.lines | order.lines).ids)

    def test_read_access_loss_is_not_mistaken_for_physical_deletion(self):
        order = self._create_sync_order()
        ids = order.lines.ids
        self.env["ir.rule"].create(
            {
                "name": "Hide synchronized line",
                "model_id": self.env["ir.model"]._get_id("pos.order.line"),
                "domain_force": repr([("id", "not in", ids)]),
                "perm_read": True,
                "perm_write": False,
                "perm_create": False,
                "perm_unlink": False,
            }
        )
        result = self.basic_config.read_config_open_orders({}, {"pos.order.line": ids})
        _logger.debug("Lost line access: %s", result["deleted_record_ids"])
        self.assertEqual(result["deleted_record_ids"].get("pos.order.line"), [])
        self.assertFalse(result["dynamic_records"]["pos.order.line"])

    def test_cancelled_known_orders_are_reported_without_a_search_domain(self):
        order = self._create_sync_order()
        order.state = "cancel"
        result = self.basic_config.read_config_open_orders({}, {"pos.order": order.ids})
        _logger.debug("Cancelled order removal: %s", result["deleted_record_ids"])
        self.assertEqual(result["deleted_record_ids"].get("pos.order"), order.ids)

    def test_pos_authorized_invoice_is_not_reported_as_deleted(self):
        order = self._create_sync_order()
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": self.basic_config.journal_id.id,
            }
        )
        order.account_move = move
        self.env["ir.rule"].create(
            {
                "name": "No direct access to synchronized move",
                "model_id": self.env["ir.model"]._get_id("account.move"),
                "domain_force": repr([("id", "!=", move.id)]),
                "perm_read": True,
                "perm_write": False,
                "perm_create": False,
                "perm_unlink": False,
            }
        )
        self.assertFalse(move._filtered_access("read"))
        result = self.basic_config.read_config_open_orders(
            {"pos.order": [("id", "=", order.id)]},
            {"pos.order": order.ids, "account.move": move.ids},
        )
        loaded_ids = [row["id"] for row in result["dynamic_records"]["account.move"]]
        _logger.debug(
            "POS-authorized moves=%s deleted=%s",
            loaded_ids,
            result["deleted_record_ids"],
        )
        self.assertIn(move.id, loaded_ids)
        self.assertNotIn(move.id, result["deleted_record_ids"].get("account.move", []))
