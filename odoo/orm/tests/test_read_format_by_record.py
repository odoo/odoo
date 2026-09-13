from odoo import fields, models
from odoo.orm.model_test_env import model_test_env
from odoo.orm.models.mixins._cache_scan import can_scan_read

_MOD = "test_read_format_by_record"


class Note(models.Model):
    _name = "rf.note"
    _module = _MOD
    _description = "a stored column the read path cannot scan from the cache"

    name = fields.Char()
    body = fields.Html(sanitize=False)


def test_a_stored_unscannable_column_reads_hits_and_misses_alike():
    with model_test_env(Note) as env:
        notes = env["rf.note"].create(
            [{"name": f"n{i}", "body": f"<p>b{i}</p>"} for i in range(6)]
        )
        field = notes._fields["body"]
        assert not can_scan_read(field)
        notes.mapped("body")
        field._invalidate_cache(env, notes[1::2].ids)
        rows = notes.read(["body"])
        assert [row["body"] for row in rows] == [f"<p>b{i}</p>" for i in range(6)]


def test_a_deleted_record_drops_out_of_the_result():
    with model_test_env(Note) as env:
        notes = env["rf.note"].create(
            [{"name": f"n{i}", "body": f"<p>b{i}</p>"} for i in range(4)]
        )
        notes.mapped("body")
        gone_id = notes[1].id
        # the row vanishes under the cache, as a concurrent delete would leave it
        env.cr.storage.remove_rows(notes._table, [gone_id])
        notes._fields["body"]._invalidate_cache(env, [gone_id])
        rows = notes.read(["body"])
        assert [row["id"] for row in rows] == [n.id for n in notes if n.id != gone_id]
