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
        # pg_size_pretty's text, units and rounding, as the SQL path answers
        assert doc.with_context(bin_size=True).raw == "8 bytes"
        for size, pretty in (
            (1024, "1024 bytes"),
            (10240, "10 kB"),
            (1500000, "1465 kB"),
            (10485760, "10 MB"),
            (15000000, "14 MB"),
        ):
            doc.raw = b"x" * size
            env.flush_all()
            env.invalidate_all()
            assert doc.with_context(bin_size=True).raw == pretty, size


def test_a_named_precision_answers_the_model_default_without_the_table():
    with model_test_env(Doc) as env:
        assert env.registry.locale.decimal_precision(env, "Product Price") == 2
        assert env["fdd.doc"]._fields["amount"].get_digits(env) == (16, 2)
        doc = env["fdd.doc"].create({"amount": 1.23456})
        assert doc.amount == 1.23


def test_a_domain_on_an_inline_binary_compares_the_base64_text():
    with model_test_env(Doc) as env:
        doc = env["fdd.doc"].create({"raw": b"aGVsbG8="})
        empty = env["fdd.doc"].create({})
        assert env["fdd.doc"].search([("raw", "=", "aGVsbG8=")]) == doc
        assert env["fdd.doc"].search([("raw", "!=", "aGVsbG8=")]) == empty
        assert (doc + empty).filtered_domain([("raw", "in", [b"aGVsbG8="])]) == doc
