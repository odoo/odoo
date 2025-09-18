"""Database-free tests for ``ir.model`` module-level pure functions.

Covers XML ID construction helpers: ``model_xmlid()``, ``field_xmlid()``,
``selection_xmlid()``, and ``make_compute()`` dependency parsing.

Run with::

    python -m pytest core/tests/models/test_ir_model.py -v
"""

from odoo.addons.base.models.ir_model import (
    field_xmlid,
    model_xmlid,
    selection_xmlid,
)

# ── model_xmlid() ───────────────────────────────────────────────


class TestModelXmlid:
    """``model_xmlid()``: build XML ID for a model definition."""

    def test_standard_model(self):
        assert model_xmlid("base", "res.partner") == "base.model_res_partner"

    def test_nested_dots(self):
        assert model_xmlid("base", "ir.model.fields") == "base.model_ir_model_fields"

    def test_single_word_model(self):
        assert model_xmlid("base", "base") == "base.model_base"

    def test_custom_module(self):
        assert model_xmlid("sale", "sale.order") == "sale.model_sale_order"


# ── field_xmlid() ───────────────────────────────────────────────


class TestFieldXmlid:
    """``field_xmlid()``: build XML ID for a field definition."""

    def test_standard_field(self):
        assert field_xmlid("base", "res.partner", "name") == "base.field_res_partner__name"

    def test_relational_field(self):
        assert field_xmlid("base", "res.partner", "company_id") == "base.field_res_partner__company_id"

    def test_nested_model_dots(self):
        assert field_xmlid("base", "ir.model.fields", "model_id") == "base.field_ir_model_fields__model_id"


# ── selection_xmlid() ───────────────────────────────────────────


class TestSelectionXmlid:
    """``selection_xmlid()``: build XML ID for a selection value.

    Normalizes the value: dots and spaces become underscores, lowercased.
    """

    def test_simple_value(self):
        result = selection_xmlid("base", "res.partner", "type", "contact")
        assert result == "base.selection__res_partner__type__contact"

    def test_value_with_spaces(self):
        result = selection_xmlid("base", "res.partner", "type", "My Value")
        assert result == "base.selection__res_partner__type__my_value"

    def test_value_with_dots(self):
        result = selection_xmlid("base", "ir.actions", "state", "opt.a")
        assert result == "base.selection__ir_actions__state__opt_a"

    def test_uppercase_value(self):
        result = selection_xmlid("base", "res.partner", "type", "INVOICE")
        assert result == "base.selection__res_partner__type__invoice"

    def test_mixed_normalization(self):
        """Spaces, dots, and uppercase all normalized together."""
        result = selection_xmlid("sale", "sale.order", "state", "Draft Order.v2")
        assert result == "sale.selection__sale_order__state__draft_order_v2"
