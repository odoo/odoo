import sys

import pytest

from odoo import fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.orm.model_test_env import model_test_env, module_model_classes

from odoo.addons.base.models.ir_access import domain_group_tests, find_access_cycle

_MOD = "test_ir_access_dbfree"


class Shelf(models.Model):
    _name = "iad.shelf"
    _module = _MOD
    _description = "a shelf"

    name = fields.Char()
    featured_book_id = fields.Many2one("iad.book")


class Book(models.Model):
    _name = "iad.book"
    _module = _MOD
    _description = "a book"

    name = fields.Char()
    shelf_id = fields.Many2one("iad.shelf")


@pytest.fixture(scope="module")
def base_env():
    with model_test_env(
        *module_model_classes("base"), Shelf, Book, check_cache=False
    ) as env:
        yield env


@pytest.fixture
def world(base_env):
    env = base_env
    env["ir.access"].search([]).unlink()
    reader, other, members = env["res.groups"].create(
        [{"name": "reader"}, {"name": "other"}, {"name": "members"}]
    )
    user = env["res.users"].create(
        {"name": "u", "login": f"u{len(env['res.users'].search([]))}"}
    )
    user.group_ids = [(4, reader.id)]
    shelf_a, shelf_b = env["iad.shelf"].create([{"name": "a"}, {"name": "b"}])
    books = env["iad.book"].create(
        [
            {"name": "one", "shelf_id": shelf_a.id},
            {"name": "two", "shelf_id": shelf_a.id},
            {"name": "three", "shelf_id": shelf_b.id},
        ]
    )
    return env, user, reader, other, members, books, shelf_a


def allow(env, model, group, domain=False, kind="permission", **kwargs):
    return env["ir.access"].create(
        {
            "name": f"{kind} {model}",
            "model_id": env["ir.model"]._get_id(model),
            "group_id": group.id,
            "kind": kind,
            "operation": kwargs.pop("operation", "r"),
            "domain": domain and str(domain),
            **kwargs,
        }
    )


def readable(user, records):
    return records.with_user(user)._filtered_access("read").with_user(records.env.user)


def test_permissions_add_up_and_guards_narrow(world):
    env, user, reader, other, _members, books, _shelf_a = world
    one, two, three = books
    assert not readable(user, books)
    allow(env, "iad.book", reader, [("id", "=", one.id)])
    allow(env, "iad.book", reader, [("id", "=", two.id)])
    allow(env, "iad.book", other, [("id", "=", three.id)])
    assert readable(user, books) == one + two
    allow(env, "iad.book", other, [("id", "!=", one.id)], kind="guard")
    assert readable(user, books) == two
    with pytest.raises(AccessError):
        one.with_user(user).check_access("read")


def test_a_member_guard_binds_its_members_only(world):
    env, user, reader, _other, members, books, _shelf_a = world
    allow(env, "iad.book", reader)
    allow(
        env,
        "iad.book",
        members,
        [("name", "=", "one")],
        kind="guard",
        guard_scope="members",
    )
    assert readable(user, books) == books
    user.group_ids = [(4, members.id)]
    assert readable(user, books) == books[0]


def test_the_access_operator_follows_the_pointed_record(world):
    env, user, reader, _other, _members, books, shelf_a = world
    allow(env, "iad.book", reader, [("shelf_id", "access", "read")])
    assert not env["iad.book"].with_user(user).has_access("read")
    allow(env, "iad.shelf", reader, [("id", "=", shelf_a.id)])
    assert readable(user, books) == books[:2]
    assert env["iad.book"].with_user(user).search([]).ids == books[:2].ids


def test_a_cycle_through_the_operator_is_refused(world):
    env, _user, reader, _other, _members, _books, _shelf_a = world
    allow(env, "iad.book", reader, [("shelf_id", "access", "read")])
    with pytest.raises(ValidationError, match="form a cycle"):
        allow(env, "iad.shelf", reader, [("featured_book_id", "access", "read")])
        env.flush_all()


def test_a_domain_testing_the_user_s_groups_is_named():
    assert domain_group_tests("[('id', 'not in', user.all_group_ids.ids)]") == [
        "all_group_ids"
    ]
    assert domain_group_tests("['!', ('id', 'in', user.group_ids.ids)]") == [
        "group_ids"
    ]
    assert domain_group_tests("[(1, '=', user.has_group('base.group_user'))]") == [
        "has_group"
    ]
    assert domain_group_tests(
        "[('id', '=', 0)] if user.has_group('base.group_user') else []"
    ) == ["has_group"]
    assert domain_group_tests("[('user_id.group_ids', '!=', False)]") == []


def test_a_domain_that_only_widens_with_the_user_s_groups_is_not_named():
    # membership in the ids of the user's groups, and a domain the members
    # of a group are exempt from, give more records to more groups
    assert domain_group_tests("[('id', 'in', user.all_group_ids.ids)]") == []
    assert domain_group_tests("[('group_ids', 'in', user.group_ids.ids)]") == []
    assert (
        domain_group_tests(
            "[] if user.has_group('base.group_user') else [('id', '=', 0)]"
        )
        == []
    )
    assert (
        domain_group_tests(
            "(['|', ('id', '=', 1)] if user.has_group('base.group_user') else [])"
            " + [('id', '=', 2)]"
        )
        == []
    )


def test_find_access_cycle():
    a, b, c = ("a", "read"), ("b", "read"), ("c", "write")
    assert find_access_cycle({a: [b], b: [c]}) is None
    assert find_access_cycle({a: [b], b: [c], c: [a]}) == [a, b, c, a]
    assert find_access_cycle({a: [a]}) == [a, a]
    assert find_access_cycle({a: [b, c], c: [b]}) is None


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
