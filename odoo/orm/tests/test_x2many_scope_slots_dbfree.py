from odoo import fields, models
from odoo.orm.fields.relational._base import PENDING_SCOPE_KEY
from odoo.orm.model_test_env import model_test_env
from odoo.tools.misc import SENTINEL


class Host(models.Model):
    _name = "scope.host"
    _module = "odoo.addons.test_scope_harness"
    _description = "Scope host"

    name = fields.Char()
    child_ids = fields.One2many("scope.child", "host_id")
    tag_ids = fields.Many2many("scope.child")
    computed_ids = fields.Many2many("scope.child", compute="_compute_computed_ids")

    def _compute_computed_ids(self):
        for host in self:
            host.computed_ids = host.child_ids


class Child(models.Model):
    _name = "scope.child"
    _module = "odoo.addons.test_scope_harness"
    _description = "Scope child"

    name = fields.Char()
    host_id = fields.Many2one("scope.host")


class Note(models.Model):
    _name = "scope.note"
    _module = "odoo.addons.test_scope_harness"
    _description = "Scope note"

    res_model = fields.Char()
    res_id = fields.Many2oneReference(model_field="res_model")


class HostWithNotes(models.Model):
    _inherit = "scope.host"
    _module = "odoo.addons.test_scope_harness"

    note_ids = fields.One2many(
        "scope.note", "res_id", domain=lambda self: [("res_model", "=", self._name)]
    )


def _slots(env, field):
    return {
        key: dict(slot)
        for key, slot in env.core.iter_context_caches(field)
        if key != PENDING_SCOPE_KEY
    }


def test_the_access_key_is_the_scope_and_none_for_a_computed_field():
    with model_test_env(Host, Child, Note, HostWithNotes) as env:
        host = env["scope.host"].create({"name": "h"})
        as_user = host.with_env(env(user=2, su=False))
        child_ids = host._fields["child_ids"]
        computed = host._fields["computed_ids"]
        assert env.get_cache_key(child_ids) == (True,)
        assert as_user.env.get_cache_key(child_ids) == ((2, None),)
        assert env.get_cache_key(computed) == (None,)
        assert as_user.env.get_cache_key(computed) == (None,)


def test_a_full_value_set_in_one_scope_evicts_the_other_scopes():
    with model_test_env(Host, Child, Note, HostWithNotes) as env:
        host = env["scope.host"].create({"name": "h"})
        a, b = env["scope.child"].create([{"name": "a"}, {"name": "b"}])
        field = host._fields["tag_ids"]
        as_user = host.with_env(env(user=2, su=False))
        field._update_cache(host, (a.id, b.id))
        field._update_cache(as_user, (a.id,), keep_other_scopes=True)
        assert _slots(env, field) == {
            (True,): {host.id: (a.id, b.id)},
            ((2, None),): {host.id: (a.id,)},
        }
        field._update_cache(as_user, (b.id,))
        assert _slots(env, field) == {(True,): {}, ((2, None),): {host.id: (b.id,)}}


def test_a_removal_reaches_every_scope_and_an_addition_only_the_superuser():
    with model_test_env(Host, Child, Note, HostWithNotes) as env:
        host = env["scope.host"].create({"name": "h"})
        a, b, c = env["scope.child"].create([{"name": n} for n in "abc"])
        field = host._fields["tag_ids"]
        as_user = host.with_env(env(user=2, su=False))
        field._update_cache(host, (a.id, b.id))
        field._update_cache(as_user, (a.id, b.id), keep_other_scopes=True)

        field._sync_other_scopes(as_user.env, host.id, removed={b.id})
        assert _slots(env, field)[(True,)] == {host.id: (a.id,)}
        assert _slots(env, field)[((2, None),)] == {host.id: (a.id, b.id)}

        field._sync_other_scopes(env, host.id, added=(c.id,))
        assert _slots(env, field)[((2, None),)] == {}
        assert _slots(env, field)[(True,)] == {host.id: (a.id,)}

        field._update_cache(as_user, (a.id,), keep_other_scopes=True)
        field._sync_other_scopes(as_user.env, host.id, added=(c.id,))
        assert _slots(env, field)[(True,)] == {host.id: (a.id, c.id)}
        assert _slots(env, field)[((2, None),)] == {host.id: (a.id,)}


def test_the_inverse_write_of_a_many2one_keeps_both_scopes_coherent():
    with model_test_env(Host, Child, Note, HostWithNotes) as env:
        host = env["scope.host"].create({"name": "h"})
        a = env["scope.child"].create({"name": "a", "host_id": host.id})
        field = host._fields["child_ids"]
        as_user = host.with_env(env(user=2, su=False))
        field._update_cache(host, (a.id,))
        field._update_cache(as_user, (a.id,), keep_other_scopes=True)

        b = env["scope.child"].create({"name": "b", "host_id": host.id})
        assert _slots(env, field)[(True,)] == {host.id: (a.id, b.id)}
        assert host.id not in _slots(env, field)[((2, None),)]

        field._update_cache(as_user, (a.id, b.id), keep_other_scopes=True)
        b.write({"host_id": False})
        assert _slots(env, field)[(True,)] == {host.id: (a.id,)}
        assert _slots(env, field)[((2, None),)] == {host.id: (a.id,)}


def test_a_many2one_reference_create_reaches_every_scope():
    with model_test_env(Host, Child, Note, HostWithNotes) as env:
        host = env["scope.host"].create({"name": "h"})
        field = host._fields["note_ids"]
        as_user = host.with_env(env(user=2, su=False))
        field._update_cache(host, ())
        field._update_cache(as_user, (), keep_other_scopes=True)

        note = env["scope.note"].create({"res_model": "scope.host", "res_id": host.id})
        assert _slots(env, field)[(True,)] == {host.id: (note.id,)}
        assert host.id not in _slots(env, field)[((2, None),)]


def test_a_pending_record_shares_one_slot_across_scopes():
    with model_test_env(Host, Child, Note, HostWithNotes) as env:
        a = env["scope.child"].create({"name": "a"})
        host = env["scope.host"].new({"name": "pending"})
        as_user = host.with_env(env(user=2, su=False))
        field = host._fields["tag_ids"]
        field._update_cache(host, (a.id,))
        assert as_user.tag_ids == a
        field._update_cache(as_user, ())
        assert not host.tag_ids
        assert dict(env.core.get_context_data(field, PENDING_SCOPE_KEY)) == {
            host.id: ()
        }


def test_a_fetch_delegated_to_the_superuser_is_served_to_the_requesting_scope():
    with model_test_env(Host, Child, Note, HostWithNotes) as env:
        host = env["scope.host"].create({"name": "h"})
        a = env["scope.child"].create({"name": "a"})
        field = host._fields["tag_ids"]
        as_user = host.with_env(env(user=2, su=False))
        env.invalidate_all()
        assert field._value_after_delegated_fetch(as_user.env, host.id) is SENTINEL
        field._update_cache(host, (a.id,))
        assert field._value_after_delegated_fetch(as_user.env, host.id) == (a.id,)
        assert _slots(env, field)[((2, None),)] == {host.id: (a.id,)}
        assert field._value_after_delegated_fetch(env, host.id) is SENTINEL


def test_a_pending_record_lists_its_x2many_in_its_record_cache():
    with model_test_env(Host, Child, Note, HostWithNotes) as env:
        a = env["scope.child"].create({"name": "a"})
        host = env["scope.host"].new({"name": "pending", "tag_ids": [(6, 0, a.ids)]})
        assert "tag_ids" in host._cache
        assert host.tag_ids._origin == a
        as_user = host.with_env(env(user=2, su=False))
        assert "tag_ids" in as_user._cache
        assert as_user._convert_to_write({"tag_ids": as_user.tag_ids}) == {
            "tag_ids": [(6, 0, [a.id])]
        }
