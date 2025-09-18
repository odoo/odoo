"""Database-free tests for ``ir.model.data`` compute methods.

Covers ``_compute_complete_name()`` (module + name joining) and
``_compute_reference()`` (model,res_id string construction).

Run with::

    python -m pytest core/tests/models/test_ir_model_data.py -v
"""


# ── _compute_complete_name ───────────────────────────────────────


class TestCompleteName:
    """``_compute_complete_name``: join module and name with dot."""

    def test_module_and_name(self, env):
        rec = env["ir.model.data"].create({
            "module": "base",
            "name": "model_res_partner",
            "model": "res.partner",
            "res_id": 0,
        })
        rec._compute_complete_name()
        assert rec.complete_name == "base.model_res_partner"

    def test_empty_module(self, env):
        """No module → just the name (no leading dot)."""
        rec = env["ir.model.data"].create({
            "module": "",
            "name": "orphan_record",
            "model": "res.partner",
            "res_id": 0,
        })
        rec._compute_complete_name()
        assert rec.complete_name == "orphan_record"

    def test_empty_name(self, env):
        """No name → just the module (no trailing dot)."""
        rec = env["ir.model.data"].create({
            "module": "base",
            "name": "",
            "model": "res.partner",
            "res_id": 0,
        })
        rec._compute_complete_name()
        assert rec.complete_name == "base"


# ── _compute_reference ──────────────────────────────────────────


class TestReference:
    """``_compute_reference``: build 'model,res_id' string."""

    def test_standard_reference(self, env):
        rec = env["ir.model.data"].create({
            "module": "base",
            "name": "partner_root",
            "model": "res.partner",
            "res_id": 42,
        })
        rec._compute_reference()
        assert rec.reference == "res.partner,42"

    def test_zero_res_id(self, env):
        rec = env["ir.model.data"].create({
            "module": "base",
            "name": "no_record",
            "model": "ir.model",
            "res_id": 0,
        })
        rec._compute_reference()
        assert rec.reference == "ir.model,0"
