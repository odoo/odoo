"""base's own models and data hosted on the DB-free tier: what R3 said could
not be done. Slow for a unit test (about half a minute, most of it the
currency and country files), and the one pin that the tier can carry a
module's real access rows."""

import sys

import pytest

from odoo.exceptions import AccessError
from odoo.orm.model_test_env import (
    load_module_data,
    model_test_env,
    module_model_classes,
)

# module rows and categories come from Module.update_list(), not a data file
_LOADER_OWNED = ("data/ir_module_module.xml",)


@pytest.fixture(scope="module")
def base_env():
    classes = module_model_classes("base")
    assert len(classes) > 140
    with model_test_env(*classes, check_cache=False) as env:
        loaded = load_module_data(env, "base", skip=_LOADER_OWNED)
        assert len(loaded) >= 66
        yield env


def test_base_hosts_its_groups_and_access_rows(base_env):
    env = base_env
    assert env["ir.access"].sudo().search_count([]) > 150
    assert env["ir.access"].sudo().search_count([("kind", "=", "guard")]) >= 10
    assert env.ref("base.user_admin").login == "admin"
    assert env.ref("base.user_admin").has_group("base.group_user")


def test_an_internal_user_reads_what_the_acls_and_rules_allow(base_env):
    env = base_env
    user = env["res.users"].create(
        {"name": "u", "login": "u", "group_ids": [(4, env.ref("base.group_user").id)]}
    )
    as_user = env(user=user.id)
    assert as_user["res.partner"].search_count([]) == 3
    with pytest.raises(AccessError):
        as_user["ir.access"].create(
            {"name": "x", "model_id": 1, "kind": "permission", "operation": "r"}
        )


def test_a_portal_user_sees_only_its_own_partner(base_env):
    env = base_env
    portal = env["res.users"].create(
        {"name": "p", "login": "p", "group_ids": [(4, env.ref("base.group_portal").id)]}
    )
    assert env(user=portal.id)["res.partner"].search_count([]) == 1


def test_an_action_created_through_a_subtype_is_read_through_the_root(base_env):
    env = base_env
    window = env["ir.actions.act_window"].search([], limit=1)
    assert window
    root = env["ir.actions.actions"].browse(window.id)
    assert root.exists() and root.type == "ir.actions.act_window"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
