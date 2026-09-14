import pytest
from psycopg.errors import ForeignKeyViolation

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.orm.model_test_env import model_test_env

_MOD = "test_unlink_foreign_keys_dbfree"


class Tag(models.Model):
    _name = "fk.tag"
    _module = _MOD
    _description = "tag"
    _log_access = False

    name = fields.Char()


class Head(models.Model):
    _name = "fk.head"
    _module = _MOD
    _description = "head"
    _log_access = False

    name = fields.Char()
    tag_ids = fields.Many2many("fk.tag")
    line_ids = fields.One2many("fk.line", "head_id")


class Line(models.Model):
    _name = "fk.line"
    _module = _MOD
    _description = "line, deleted with its head"
    _log_access = False

    head_id = fields.Many2one("fk.head", ondelete="cascade")
    name = fields.Char()
    note_ids = fields.One2many("fk.note", "line_id")


class Note(models.Model):
    _name = "fk.note"
    _module = _MOD
    _description = "note, orphaned when its line goes"
    _log_access = False

    line_id = fields.Many2one("fk.line")
    tag_id = fields.Many2one("fk.tag", ondelete="restrict")
    body = fields.Char()


@pytest.fixture
def env():
    with model_test_env(Tag, Head, Line, Note) as env:
        yield env


def _tree(env):
    tags = env["fk.tag"].create([{"name": "a"}, {"name": "b"}])
    head = env["fk.head"].create(
        {
            "name": "h",
            "tag_ids": [(6, 0, tags.ids)],
            "line_ids": [(0, 0, {"name": "l1"}), (0, 0, {"name": "l2"})],
        }
    )
    note = env["fk.note"].create({"line_id": head.line_ids[0].id, "body": "n"})
    return tags, head, note


def test_a_cascade_column_deletes_the_referencing_rows_and_their_dependents(env):
    tags, head, note = _tree(env)
    lines = head.line_ids
    head.unlink()
    assert not lines.exists()
    assert not env["fk.line"].search([])
    # the note's many2one is 'set null': the note survives, unlinked from its line
    assert note.exists() and not note.line_id
    assert tags.exists() == tags


def test_a_deleted_record_leaves_no_many2many_relation_row(env):
    tags, head, _note = _tree(env)
    tags[0].unlink()
    assert head.tag_ids == tags[1]
    head.unlink()
    assert not env.cr.storage.get_table_ids("fk_head_fk_tag_rel")


def test_a_restrict_column_refuses_the_delete_like_the_database(env):
    tags, _head, note = _tree(env)
    note.tag_id = tags[1]
    with pytest.raises(ForeignKeyViolation):
        tags[1].unlink()
    assert tags[1].exists()


class Account(models.Model):
    _name = "fk.account"
    _module = _MOD
    _description = "account, referenced per company"
    _log_access = False

    name = fields.Char()


class Partner(models.Model):
    _name = "fk.partner"
    _module = _MOD
    _description = "partner with company-dependent accounts"
    _log_access = False

    name = fields.Char()
    receivable_id = fields.Many2one(
        "fk.account", company_dependent=True, ondelete="restrict"
    )
    payable_id = fields.Many2one("fk.account", company_dependent=True)
    label = fields.Char(compute="_compute_label", store=True)

    @api.depends("payable_id")
    def _compute_label(self):
        for partner in self:
            partner.label = partner.payable_id.display_name or "none"


def test_a_company_dependent_reference_refuses_or_clears_the_unlink():
    with model_test_env(Account, Partner) as env:
        keep, gone, other = env["fk.account"].create(
            [{"name": "keep"}, {"name": "gone"}, {"name": "other"}]
        )
        partner = env["fk.partner"].create(
            {"name": "p", "receivable_id": keep.id, "payable_id": gone.id}
        )
        env.flush_all()
        assert partner.label == "gone"
        # the json object the foreign keys do not see: refused on restrict
        with pytest.raises(UserError, match="used by"):
            keep.unlink()
        assert keep.exists()
        # cleared otherwise, and the dependents recompute
        gone.unlink()
        env.flush_all()
        env.invalidate_all()
        assert partner.payable_id == env["fk.account"]
        assert partner.receivable_id == keep
        assert partner.label == "none"
        other.unlink()
        assert not other.exists()
