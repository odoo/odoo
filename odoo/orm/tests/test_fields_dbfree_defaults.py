import pytest

from odoo import fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_fields_dbfree_defaults"


class Doc(models.Model):
    _name = "fdd.doc"
    _module = _MOD
    _description = "a document with a file and a priced amount"

    data = fields.Binary()
    raw = fields.Binary(attachment=False)
    amount = fields.Float(digits="Product Price")


def test_an_attachment_backed_binary_reads_empty_and_refuses_a_write_without_a_table():
    with model_test_env(Doc) as env:
        doc = env["fdd.doc"].create({})
        assert doc.data is False
        with pytest.raises(NotImplementedError, match=r"ir\.attachment"):
            doc.data = b"aGVsbG8="


def test_an_inline_binary_answers_its_size_under_bin_size():
    with model_test_env(Doc) as env:
        doc = env["fdd.doc"].create({"raw": b"aGVsbG8="})
        env.flush_all()
        env.invalidate_all()
        assert doc.raw == b"aGVsbG8="
        assert doc.with_context(bin_size=True).raw.endswith(b"bytes")


def test_a_named_precision_answers_the_model_default_without_the_table():
    with model_test_env(Doc) as env:
        assert env.registry.locale.decimal_precision(env, "Product Price") == 2
        assert env["fdd.doc"]._fields["amount"].get_digits(env) == (16, 2)
        doc = env["fdd.doc"].create({"amount": 1.23456})
        assert doc.amount == 1.23
