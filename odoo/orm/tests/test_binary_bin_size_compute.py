"""`bin_size_field` answers a human-readable size in place of the content.

A stored field's column holds the content, so the two cannot be combined: the
cache would carry "5.00 bytes" where the column carries the bytes, and the
cache check reports `CacheInvalidError` on the next fetch. Both users of the
attribute in the workspace are non-stored, so the combination was never
refused and never worked.
"""

import pytest

from odoo import api, fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_binary_bin_size_compute"


class Doc(models.Model):
    _name = "bbs.doc"
    _module = _MOD
    _description = "doc"
    _log_access = False

    size = fields.Integer()
    body = fields.Binary(compute="_compute_body", bin_size_field="size")

    @api.depends("size")
    def _compute_body(self):
        for record in self:
            record.body = b"x" * max(record.size, 0)


def test_a_non_stored_bin_size_field_answers_a_human_size():
    with model_test_env(Doc) as env:
        record = env["bbs.doc"].create({"size": 2048})
        assert record.with_context(bin_size=True).body == b"2.00 Kb"


def test_the_content_is_still_there_without_the_context():
    with model_test_env(Doc) as env:
        record = env["bbs.doc"].create({"size": 4})
        assert record.body == b"xxxx"


def test_a_stored_bin_size_field_is_refused_at_setup():
    class StoredDoc(models.Model):
        _name = "bbs.stored"
        _module = _MOD + "_stored"
        _description = "stored doc"
        _log_access = False

        size = fields.Integer()
        body = fields.Binary(
            compute="_compute_body",
            bin_size_field="size",
            store=True,
            attachment=False,
        )

        @api.depends("size")
        def _compute_body(self):
            for record in self:
                record.body = b"x" * max(record.size, 0)

    with pytest.raises(TypeError, match="cannot be stored"):
        with model_test_env(StoredDoc):
            pass
