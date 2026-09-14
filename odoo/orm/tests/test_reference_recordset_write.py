import pytest

from odoo import fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_reference_recordset_write"


class Target(models.Model):
    _name = "refw.target"
    _module = _MOD
    _description = "target"
    _log_access = False

    name = fields.Char()


class Holder(models.Model):
    _name = "refw.holder"
    _module = _MOD
    _description = "holder"
    _log_access = False

    name = fields.Char()
    ref = fields.Reference([("refw.target", "Target")])


def test_dangling_recordset_write_is_dropped():
    with model_test_env(Target, Holder) as env:
        holder = env["refw.holder"].create({"name": "h"})
        holder.write({"ref": env["refw.target"].browse(99999)})
        assert not holder.ref


def test_existing_recordset_write_verifies_and_memoizes():
    with model_test_env(Target, Holder) as env:
        target = env["refw.target"].create({"name": "t"})
        holder = env["refw.holder"].create({"name": "h"})
        holder.write({"ref": target})
        assert holder.ref == target
        field = holder._fields["ref"]
        assert ("refw.target", target.id) in field._get_verified_pairs(env)


def test_create_with_recordset_stores_the_reference():
    with model_test_env(Target, Holder) as env:
        target = env["refw.target"].create({"name": "t"})
        holder = env["refw.holder"].create({"name": "h", "ref": target})
        assert holder.ref == target


def test_create_with_dangling_recordset_is_dropped():
    with model_test_env(Target, Holder) as env:
        holder = env["refw.holder"].create(
            {"name": "h", "ref": env["refw.target"].browse(99999)}
        )
        assert not holder.ref


def test_create_with_string_reference_still_works():
    with model_test_env(Target, Holder) as env:
        target = env["refw.target"].create({"name": "t"})
        holder = env["refw.holder"].create(
            {"name": "h", "ref": f"refw.target,{target.id}"}
        )
        assert holder.ref == target


def test_a_new_record_is_refused_at_assignment_not_at_the_read():
    with model_test_env(Target, Holder) as env:
        unsaved = env["refw.target"].new({"name": "t"})
        holder = env["refw.holder"].create({"name": "h"})
        with pytest.raises(ValueError, match="save the record first"):
            holder.ref = unsaved
        with pytest.raises(ValueError, match="save the record first"):
            env["refw.holder"].new({"ref": unsaved})
        assert not holder.ref


def test_an_empty_recordset_still_clears_the_field():
    with model_test_env(Target, Holder) as env:
        target = env["refw.target"].create({"name": "t"})
        holder = env["refw.holder"].create({"name": "h", "ref": target})
        holder.ref = env["refw.target"]
        assert not holder.ref


def test_a_domain_on_a_reference_compares_the_model_id_form():
    with model_test_env(Target, Holder) as env:
        target = env["refw.target"].create({"name": "t"})
        doc = env["refw.holder"].create({"ref": f"refw.target,{target.id}"})
        other = env["refw.holder"].create({})
        both = doc + other
        value = f"refw.target,{target.id}"
        # search and the Python predicate agree, as they do on PostgreSQL
        assert env["refw.holder"].search([("ref", "=", value)]) == doc
        assert both.filtered_domain([("ref", "=", value)]) == doc
        assert both.filtered_domain([("ref", "in", [value])]) == doc
        assert both.filtered_domain([("ref", "!=", value)]) == other
        assert both.filtered_domain([("ref", "like", "refw.target")]) == doc
        assert both.filtered_domain([("ref", "=", False)]) == other
        # an inequality compares the text, as the column does; NULL never sorts
        assert both.filtered_domain([("ref", ">=", "refw")]) == doc
        assert both.filtered_domain([("ref", "<", "refw")]) == env["refw.holder"]
        assert both.filtered_domain([("ref", "=~", r"target,\d+$")]) == doc
