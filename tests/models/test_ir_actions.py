"""Database-free tests for ``ir.actions`` validation and compute methods.

Covers ``_check_path()`` (action URL path validation) and
``_check_view_mode()`` (duplicate/space detection in view modes).

Run with::

    python -m pytest core/tests/models/test_ir_actions.py -v
"""

import re

import pytest

from odoo.exceptions import ValidationError

# ── _check_path (per-record validation logic) ─────────────────


class TestCheckPath:
    """``_check_path``: validate action URL path format.

    Tests the per-record regex and prefix rules. The cross-table
    SQL uniqueness check is skipped (requires real database).
    """

    def test_valid_path(self, env):
        """Lowercase alphanumeric with dashes/underscores passes."""
        action = env["ir.actions.act_window"].create({
            "name": "Test Action",
            "res_model": "res.partner",
            "path": "my-action_1",
            "view_mode": "list",
        })
        # No exception means it passed validation
        assert action.path == "my-action_1"

    def test_uppercase_rejected(self, env):
        """Uppercase letters are rejected by the regex."""
        with pytest.raises(ValidationError):
            env["ir.actions.act_window"].create({
                "name": "Test",
                "res_model": "res.partner",
                "path": "MyAction",
                "view_mode": "list",
            })

    def test_starts_with_digit_rejected(self, env):
        """Path must start with a letter."""
        with pytest.raises(ValidationError):
            env["ir.actions.act_window"].create({
                "name": "Test",
                "res_model": "res.partner",
                "path": "1action",
                "view_mode": "list",
            })

    def test_reserved_prefix_m_dash(self, env):
        """'m-' prefix is reserved."""
        with pytest.raises(ValidationError):
            env["ir.actions.act_window"].create({
                "name": "Test",
                "res_model": "res.partner",
                "path": "m-settings",
                "view_mode": "list",
            })

    def test_reserved_prefix_action_dash(self, env):
        """'action-' prefix is reserved."""
        with pytest.raises(ValidationError):
            env["ir.actions.act_window"].create({
                "name": "Test",
                "res_model": "res.partner",
                "path": "action-open",
                "view_mode": "list",
            })

    def test_reserved_word_new(self, env):
        """'new' is a reserved path."""
        with pytest.raises(ValidationError):
            env["ir.actions.act_window"].create({
                "name": "Test",
                "res_model": "res.partner",
                "path": "new",
                "view_mode": "list",
            })

    def test_no_path_passes(self, env):
        """No path set → no validation needed."""
        action = env["ir.actions.act_window"].create({
            "name": "Test Action",
            "res_model": "res.partner",
            "view_mode": "list",
        })
        assert not action.path

    def test_special_chars_rejected(self, env):
        """Spaces and special characters are rejected."""
        with pytest.raises(ValidationError):
            env["ir.actions.act_window"].create({
                "name": "Test",
                "res_model": "res.partner",
                "path": "my action",
                "view_mode": "list",
            })


# ── _check_path regex (pure, no env needed) ───────────────────


class TestPathRegex:
    """Test the regex pattern used in ``_check_path`` independently."""

    PATTERN = re.compile(r"[a-z][a-z0-9_-]*")

    def test_valid_paths(self):
        valid = ["settings", "my-page", "a", "test_path", "abc123"]
        for path in valid:
            assert self.PATTERN.fullmatch(path), f"{path!r} should be valid"

    def test_invalid_paths(self):
        invalid = ["", "1abc", "A", "my path", "-start", "_start"]
        for path in invalid:
            assert not self.PATTERN.fullmatch(path), f"{path!r} should be invalid"


# ── _check_view_mode ──────────────────────────────────────────


class TestCheckViewMode:
    """``_check_view_mode``: reject duplicate or space-containing view modes."""

    def test_valid_single_mode(self, env):
        """Single mode passes."""
        action = env["ir.actions.act_window"].create({
            "name": "Test",
            "res_model": "res.partner",
            "view_mode": "list",
        })
        assert action.view_mode == "list"

    def test_valid_multiple_modes(self, env):
        """Comma-separated distinct modes pass."""
        action = env["ir.actions.act_window"].create({
            "name": "Test",
            "res_model": "res.partner",
            "view_mode": "list,form,kanban",
        })
        assert action.view_mode == "list,form,kanban"

    def test_duplicate_mode_rejected(self, env):
        """Duplicate mode values raise ValidationError."""
        with pytest.raises(ValidationError):
            env["ir.actions.act_window"].create({
                "name": "Test",
                "res_model": "res.partner",
                "view_mode": "list,form,list",
            })

    def test_space_in_mode_rejected(self, env):
        """A bare space as a mode entry raises ValidationError.

        The constraint splits on ',' and checks if ``" "`` is in the
        resulting list. ``"list, ,form"`` → ``["list", " ", "form"]``.
        """
        with pytest.raises(ValidationError):
            env["ir.actions.act_window"].create({
                "name": "Test",
                "res_model": "res.partner",
                "view_mode": "list, ,form",
            })
