import ast

from odoo.addons.base.models.ir_access_convert import (
    GROUP_EVERYONE,
    NOTHING,
    convert,
    normalize_domain,
    reach,
)

OWN = "[('user_id', '=', user.id)]"
TEAM = "[('team_id', 'in', user.team_ids.ids)]"
COMPANY = "[('company_id', 'in', company_ids)]"

IMPLIED = {
    "base.group_user": [],
    "base.group_portal": [],
    "base.group_public": [],
    "sale.group_own": ["base.group_user"],
    "sale.group_all": ["sale.group_own"],
    "sale.group_manager": ["sale.group_all"],
    "account.group_invoice": ["base.group_user"],
    "stock.group_user": ["base.group_user"],
}


def acl(xmlid, group, perms="crud", model="sale.order", **extra):
    return {
        "xmlid": xmlid,
        "model": model,
        "group": group,
        "perm_create": "c" in perms,
        "perm_read": "r" in perms,
        "perm_write": "u" in perms,
        "perm_unlink": "d" in perms,
        **extra,
    }


def rule(xmlid, groups, domain, perms=None, model="sale.order", **extra):
    values = {"xmlid": xmlid, "model": model, "groups": groups, "domain_force": domain}
    if perms is not None:
        values.update(
            perm_create="c" in perms,
            perm_read="r" in perms,
            perm_write="u" in perms,
            perm_unlink="d" in perms,
        )
    return values | extra


def shape(rows):
    return sorted(
        (row["kind"], row["guard_scope"], row["group"], row["operation"], row["domain"])
        for row in rows
    )


def test_acl_alone_is_a_see_all_permission_and_keeps_its_xmlid():
    rows, report = convert(
        [acl("sale.access_order", "sale.group_own", "cru")], [], IMPLIED
    )
    assert shape(rows) == [("permission", None, "sale.group_own", "cru", "")]
    assert rows[0]["xmlid"] == "sale.access_order"
    assert rows[0]["module"] == "sale"
    assert report.xmlid_map == {"sale.access_order": ["sale.access_order"]}
    assert not report.changes and not report.monotonicity


def test_groupless_acl_belongs_to_everyone():
    rows, _report = convert([acl("base.access_country", None, "r")], [], IMPLIED)
    assert shape(rows) == [("permission", None, GROUP_EVERYONE, "r", "")]


def test_global_rule_is_a_guard_on_everyone_with_its_modes():
    rows, report = convert(
        [acl("sale.access_order", "sale.group_own")],
        [rule("sale.rule_company", [], COMPANY, perms="r")],
        IMPLIED,
    )
    assert shape(rows) == [
        ("guard", "everyone", GROUP_EVERYONE, "r", COMPANY),
        ("permission", None, "sale.group_own", "crud", ""),
    ]
    assert not report.changes


def test_restrict_rule_is_a_guard_scoped_to_its_members():
    rows, report = convert(
        [acl("sale.access_order", "sale.group_own")],
        [rule("sale.rule_own", ["sale.group_own"], OWN, composition="restrict")],
        IMPLIED,
    )
    assert shape(rows) == [
        ("guard", "members", "sale.group_own", "crud", OWN),
        ("permission", None, "sale.group_own", "crud", ""),
    ]
    assert not report.changes
    assert not report.dead_rules


def test_grant_rule_limits_only_its_modes_on_its_group():
    rows, report = convert(
        [acl("sale.access_order", "sale.group_own")],
        [rule("sale.rule_own", ["sale.group_own"], OWN, perms="r")],
        IMPLIED,
    )
    assert shape(rows) == [
        ("permission", None, "sale.group_own", "cud", ""),
        ("permission", None, "sale.group_own", "r", OWN),
    ]
    assert {row["xmlid"] for row in rows} == {"sale.access_order", "sale.rule_own"}
    assert report.xmlid_map["sale.rule_own"] == ["sale.rule_own"]
    assert not report.changes


def test_rule_of_an_implied_group_binds_the_acl_of_the_implying_group():
    rows, report = convert(
        [acl("sale.access_order_manager", "sale.group_manager", "cu")],
        [rule("sale.rule_own", ["sale.group_own"], OWN)],
        IMPLIED,
    )
    assert shape(rows) == [("permission", None, "sale.group_manager", "cu", OWN)]
    assert not report.changes


def test_rule_of_an_implying_group_takes_the_acl_of_the_implied_group():
    rows, report = convert(
        [acl("sale.access_order", "sale.group_own")],
        [
            rule("sale.rule_own", ["sale.group_own"], OWN),
            rule("sale.rule_all", ["sale.group_all"], "[(1, '=', 1)]"),
        ],
        IMPLIED,
    )
    assert shape(rows) == [
        ("permission", None, "sale.group_all", "crud", ""),
        ("permission", None, "sale.group_own", "crud", OWN),
    ]
    assert not report.changes
    assert not report.monotonicity


def test_non_monotone_pair_is_reported_and_converted_monotone():
    rows, report = convert(
        [
            acl("account.access_order_invoice", "account.group_invoice", "r"),
            acl("sale.access_order", "sale.group_own"),
        ],
        [rule("sale.rule_own", ["sale.group_own"], OWN)],
        IMPLIED,
    )
    assert shape(rows) == [
        ("permission", None, "account.group_invoice", "r", ""),
        ("permission", None, "sale.group_own", "crud", OWN),
    ]
    [entry] = [
        e
        for e in report.monotonicity
        if e["alone"] == "account.group_invoice" and e["added"] == "sale.group_own"
    ]
    assert entry["operation"] == "r"
    assert entry["old_alone"] == "all"
    assert entry["old_both"] == OWN
    assert entry["new_both"] == "all"
    assert entry["added_has_access"] is True
    assert entry["roles"] == ["base.group_user"]
    widened = {(c["principal"], c["operation"], c["direction"]) for c in report.changes}
    assert ("account.group_invoice + sale.group_own", "r", "widens") in widened
    assert report.see_all_beside_rules == [
        {
            "acl": "account.access_order_invoice",
            "model": "sale.order",
            "group": "account.group_invoice",
            "operation": "r",
            "rule_groups": ["sale.group_own"],
        }
    ]


def test_restriction_group_without_access_is_dead_and_reported():
    rows, report = convert(
        [acl("stock.access_order", "stock.group_user", "r")],
        [rule("sale_team.rule_own", ["sale.group_own"], OWN)],
        {**IMPLIED, "sale.group_own": []},
    )
    assert shape(rows) == [("permission", None, "stock.group_user", "r", "")]
    assert report.dead_rules == [
        {
            "rule": "sale_team.rule_own",
            "model": "sale.order",
            "group": "sale.group_own",
            "operation": "crud",
            "domain": OWN,
            "whole": True,
        }
    ]
    [entry] = report.monotonicity
    assert (entry["alone"], entry["added"]) == ("stock.group_user", "sale.group_own")
    assert entry["added_has_access"] is False


def test_groupless_acl_beside_a_portal_rule_widens_the_portal():
    rows, report = convert(
        [acl("base.access_order_all", None, "r")],
        [rule("portal.rule_order", ["base.group_portal"], OWN, perms="r")],
        IMPLIED,
    )
    assert shape(rows) == [("permission", None, GROUP_EVERYONE, "r", "")]
    assert not report.dead_rules
    assert any(
        e["alone"] == GROUP_EVERYONE and e["added"] == "base.group_portal"
        for e in report.monotonicity
    )


def test_rule_that_only_counts_beside_another_groups_acl_narrows():
    _rows, report = convert(
        [
            acl("sale.access_order", "sale.group_own", "crud"),
            acl("account.access_order", "account.group_invoice", "r"),
        ],
        [
            rule("sale.rule_own", ["sale.group_own"], OWN),
            rule("account.rule_all", ["account.group_invoice"], "[]"),
        ],
        IMPLIED,
    )
    narrowed = {
        (c["principal"], c["operation"])
        for c in report.changes
        if c["direction"] == "narrows"
    }
    assert ("account.group_invoice + sale.group_own", "cud") in narrowed
    [dead] = report.dead_rules
    assert (dead["rule"], dead["operation"], dead["whole"]) == (
        "account.rule_all",
        "cud",
        False,
    )


def test_mode_blind_rule_governs_every_operation_and_is_listed():
    rows, report = convert(
        [acl("sale.access_order", "sale.group_own")],
        [rule("sale.rule_own", ["sale.group_own"], OWN)],
        IMPLIED,
    )
    assert shape(rows) == [("permission", None, "sale.group_own", "crud", OWN)]
    assert report.mode_blind_rules == ["sale.rule_own"]
    _rows, declared = convert(
        [acl("sale.access_order", "sale.group_own")],
        [rule("sale.rule_own", ["sale.group_own"], OWN, perms="crud")],
        IMPLIED,
    )
    assert declared.mode_blind_rules == []


def test_domain_testing_groups_is_listed():
    _rows, report = convert(
        [acl("sale.access_order", "sale.group_own")],
        [rule("sale.rule_x", [], "[('id', 'in', user.all_group_ids.ids)]")],
        IMPLIED,
    )
    assert report.group_test_domains == ["sale.rule_x"]


def test_unconvertible_sources_are_listed():
    rows, report = convert(
        [
            acl("sale.access_off", "sale.group_own", active=False),
            acl("sale.access_nomodel", "sale.group_own", model=None),
        ],
        [
            rule("sale.rule_off", [], OWN, active=False),
            rule("sale.rule_none", [], OWN, perms=""),
            rule("sale.rule_odd", [], OWN, composition="deny"),
        ],
        IMPLIED,
    )
    assert rows == []
    assert [u["source"] for u in report.unmapped] == [
        "sale.access_off",
        "sale.access_nomodel",
        "sale.rule_off",
        "sale.rule_none",
        "sale.rule_odd",
    ]


def test_multi_group_rule_names_each_row_after_its_group():
    rows, report = convert(
        [
            acl("sale.access_own", "sale.group_own"),
            acl("account.access_invoice", "account.group_invoice"),
        ],
        [rule("sale.rule_both", ["sale.group_own", "account.group_invoice"], OWN)],
        IMPLIED,
    )
    assert sorted(row["xmlid"] for row in rows) == [
        "sale.rule_both_group_invoice",
        "sale.rule_both_group_own",
    ]
    assert report.xmlid_map["sale.rule_both"] == [
        "sale.rule_both_group_invoice",
        "sale.rule_both_group_own",
    ]


DEPS = {
    "sale": {"sale", "base"},
    "sale_ext": {"sale_ext", "sale", "base"},
    "stock": {"stock", "base"},
}


def test_a_rule_of_a_module_the_line_does_not_load_makes_a_conditional_row():
    # the line's module is installed without sale_ext: there its line sees
    # all, and sale_ext deactivates that row where it restricts the group
    rows, report = convert(
        [acl("sale.access_order", "sale.group_own")],
        [rule("sale_ext.rule_own", ["sale.group_own"], OWN)],
        IMPLIED,
        module_deps=DEPS,
    )
    assert [
        (row["xmlid"], row["module"], row["operation"], row["domain"]) for row in rows
    ] == [
        ("sale.access_order_crud", "sale", "crud", ""),
        ("sale_ext.rule_own", "sale_ext", "crud", OWN),
    ]
    assert [row["deactivated_by"] for row in rows] == [["sale_ext"], []]
    assert report.xmlid_map["sale.access_order"] == [
        "sale.access_order_crud",
        "sale_ext.rule_own",
    ]


def test_without_module_dependencies_every_rule_restricts_every_line():
    # the database's own conversion: everything it holds is installed
    rows, _report = convert(
        [acl("sale.access_order", "sale.group_own")],
        [rule("sale_ext.rule_own", ["sale.group_own"], OWN)],
        IMPLIED,
    )
    assert shape(rows) == [("permission", None, "sale.group_own", "crud", OWN)]
    assert all(not row["deactivated_by"] for row in rows)


def test_row_lands_in_the_module_that_depends_on_the_other():
    rows, report = convert(
        [acl("sale_ext.access_order", "sale.group_own")],
        [rule("sale.rule_own", ["sale.group_own"], OWN)],
        IMPLIED,
        module_deps=DEPS,
    )
    assert [(row["xmlid"], row["module"]) for row in rows] == [
        ("sale_ext.rule_own", "sale_ext")
    ]
    assert not report.unmapped
    assert not report.unplaced


def test_a_pair_no_module_loads_with_both_is_left_unplaced():
    rows, report = convert(
        [acl("stock.access_order", "sale.group_own")],
        [rule("sale.rule_own", ["sale.group_own"], OWN)],
        IMPLIED,
        module_deps=DEPS,
    )
    assert [(row["xmlid"], row["deactivated_by"]) for row in rows] == [
        ("stock.access_order_crud", ["sale"])
    ]
    assert report.unplaced == [
        {
            "acl": "stock.access_order",
            "rule": "sale.rule_own",
            "model": "sale.order",
            "group": "sale.group_own",
            "operation": "crud",
        }
    ]


def test_names_depend_on_the_row_s_own_sources_only():
    # the same rule and line name the same row whether or not a module that
    # pairs the rule with another line is there
    alone, _report = convert(
        [acl("sale.access_order", "sale.group_own", "r")],
        [rule("sale.rule_own", ["sale.group_own"], OWN, perms="r")],
        IMPLIED,
        module_deps=DEPS,
    )
    beside, _report = convert(
        [
            acl("sale.access_order", "sale.group_own", "r"),
            acl("sale_ext.access_manager", "sale.group_manager", "r"),
        ],
        [rule("sale.rule_own", ["sale.group_own"], OWN, perms="r")],
        IMPLIED,
        module_deps=DEPS,
    )
    assert [row["xmlid"] for row in alone] == ["sale.rule_own"]
    assert {row["xmlid"] for row in beside} >= {
        "sale.rule_own",
        "sale_ext.rule_own_group_manager",
    }


def test_a_line_that_grants_nothing_keeps_a_row_that_admits_nothing():
    rows, report = convert([acl("sale.access_none", "sale.group_own", "")], [], IMPLIED)
    assert shape(rows) == [("permission", None, "sale.group_own", "r", NOTHING)]
    assert rows[0]["xmlid"] == "sale.access_none"
    assert not report.unmapped
    assert reach(rows, "r", frozenset({"sale.group_own"})).grants is None


def test_a_fully_absorbed_line_maps_to_the_row_that_absorbed_it():
    rows, report = convert(
        [
            acl("sale.access_order", "sale.group_own", "r"),
            acl("sale.access_manager", "sale.group_manager", "r"),
        ],
        [],
        IMPLIED,
    )
    assert [row["xmlid"] for row in rows] == ["sale.access_order"]
    assert [row["xmlid"] for row in report.source_map["sale.access_manager"]] == [
        "sale.access_order"
    ]
    assert report.xmlid_map["sale.access_manager"] == ["sale.access_order"]


def test_see_all_row_absorbs_a_narrower_row_of_an_implying_group():
    rows, report = convert(
        [
            acl("sale.access_own", "sale.group_own", "r"),
            acl("sale.access_manager", "sale.group_manager", "crud"),
        ],
        [],
        IMPLIED,
    )
    assert shape(rows) == [
        ("permission", None, "sale.group_manager", "cud", ""),
        ("permission", None, "sale.group_own", "r", ""),
    ]
    assert report.xmlid_map["sale.access_manager"] == [
        "sale.access_manager",
        "sale.access_own",
    ]
    assert not report.changes


def test_see_all_rows_of_one_group_in_two_modules_are_both_kept():
    rows, report = convert(
        [
            acl("sale.access_order", "sale.group_own", "r"),
            acl("stock.access_order", "sale.group_own", "r"),
        ],
        [],
        IMPLIED,
    )
    assert {row["xmlid"] for row in rows} == {"sale.access_order", "stock.access_order"}
    assert not report.changes


def test_database_rows_without_xmlid_convert_under_their_id():
    rows, report = convert(
        [
            {
                "id": 7,
                "model": "sale.order",
                "group": "sale.group_own",
                "perm_read": True,
            }
        ],
        [
            {
                "id": 9,
                "model": "sale.order",
                "groups": ["sale.group_own"],
                "domain_force": OWN,
                "perm_read": True,
                "perm_write": False,
                "perm_create": False,
                "perm_unlink": False,
            }
        ],
        IMPLIED,
    )
    assert shape(rows) == [("permission", None, "sale.group_own", "r", OWN)]
    assert rows[0]["xmlid"] is None
    assert rows[0]["sources"] == ["ir.model.access#7", "ir.rule#9"]
    assert report.xmlid_map == {}


def test_true_domains_normalize_to_empty():
    assert normalize_domain(None) == ""
    assert normalize_domain(" [] ") == ""
    assert normalize_domain("[(1, '=', 1)]") == ""
    assert normalize_domain('[(1,"=",1)]') == ""
    assert normalize_domain("[(0, '=', 1)]") == "[(0, '=', 1)]"


def test_a_commented_domain_normalizes_to_one_line_that_still_parses():
    domain = """[("user_id.employee_id", "any", [
        "|",
        ("parent_id", "child_of", user.employee_id.id),      # direct manager
        ("department_id.manager_id.user_id", "=", user.id),  # department manager
    ])]"""
    normalized = normalize_domain(domain)
    assert "\\n" not in normalized
    assert "#" not in normalized
    assert ast.literal_eval(
        normalized.replace("user.employee_id.id", "1").replace("user.id", "1")
    ) == [
        (
            "user_id.employee_id",
            "any",
            [
                "|",
                ("parent_id", "child_of", 1),
                ("department_id.manager_id.user_id", "=", 1),
            ],
        )
    ]
    assert normalize_domain("[('name', '=', 'a # b')]") == "[('name', '=', 'a # b')]"


def test_exclusive_roles_are_never_combined():
    _rows, report = convert(
        [acl("sale.access_order", "base.group_user", "r")],
        [rule("portal.rule_order", ["base.group_portal"], OWN)],
        IMPLIED,
    )
    assert not report.monotonicity
    assert all(
        "group_user + base.group_portal" not in c["principal"] for c in report.changes
    )


def test_a_rule_with_no_group_that_is_not_global_binds_nobody():
    rows, report = convert(
        [acl("approval.access_request", "sale.group_own")],
        [
            rule(
                "approval.request_unlink",
                [],
                "[('state', '=', 'cancel')]",
                "d",
                **{"global": False},
            )
        ],
        IMPLIED,
    )
    assert shape(rows) == [("permission", None, "sale.group_own", "crud", "")]
    assert report.bound_nobody == ["approval.request_unlink"]
    rows, _report = convert(
        [acl("approval.access_request", "sale.group_own")],
        [rule("approval.request_unlink", [], "[('state', '=', 'cancel')]", "d")],
        IMPLIED,
    )
    assert (
        "guard",
        "everyone",
        GROUP_EVERYONE,
        "d",
        "[('state', '=', 'cancel')]",
    ) in shape(rows)
