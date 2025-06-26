import { expect, test } from "@odoo/hoot";

import { makeMockEnv } from "@web/../tests/web_test_helpers";

import { condition, expression } from "@web/core/tree_editor/condition_tree";
import { domainFromTree } from "@web/core/tree_editor/domain_from_tree";

test("domainFromTree", async () => {
    await makeMockEnv();
    const toTest = [
        {
            tree: condition("foo", "=", false),
            result: `[("foo", "=", False)]`,
        },
        {
            tree: condition("foo", "=", false, true),
            result: `["!", ("foo", "=", False)]`,
        },
        {
            tree: condition("foo", "=?", false),
            result: `[("foo", "=?", False)]`,
        },
        {
            tree: condition("foo", "=?", false, true),
            result: `["!", ("foo", "=?", False)]`,
        },
        {
            tree: condition("foo", "starts_with", "hello"),
            result: `[("foo", "=ilike", "hello%")]`,
        },
        {
            tree: condition("foo", "ends_with", "hello"),
            result: `[("foo", "=ilike", "%hello")]`,
        },
        {
            tree: condition("foo", "next", [1, "weeks", "date"]),
            result: `["&", ("foo", ">=", context_today().strftime("%Y-%m-%d")), ("foo", "<=", (context_today() + relativedelta(weeks = 1)).strftime("%Y-%m-%d"))]`,
        },
        {
            tree: condition("foo", "last", [1, "months", "date"]),
            result: `["&", ("foo", ">=", (context_today() + relativedelta(months = -1)).strftime("%Y-%m-%d")), ("foo", "<=", context_today().strftime("%Y-%m-%d"))]`,
        },
        {
            tree: condition("foo", "next", [1, "weeks", "datetime"]),
            result: `["&", ("foo", ">=", datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")), ("foo", "<=", datetime.datetime.combine(context_today() + relativedelta(weeks = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S"))]`,
        },
        {
            tree: condition("foo", "last", [1, "months", "datetime"]),
            result: `["&", ("foo", ">=", datetime.datetime.combine(context_today() + relativedelta(months = -1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")), ("foo", "<=", datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S"))]`,
        },
        {
            tree: condition("foo", "next", [1, "weeks", "date"], true),
            result: `["!", "&", ("foo", ">=", context_today().strftime("%Y-%m-%d")), ("foo", "<=", (context_today() + relativedelta(weeks = 1)).strftime("%Y-%m-%d"))]`,
        },
        {
            tree: condition("foo", "last", [expression("a"), "weeks", "date"], true),
            result: `["!", "&", ("foo", ">=", (context_today() + relativedelta(weeks = a)).strftime("%Y-%m-%d")), ("foo", "<=", context_today().strftime("%Y-%m-%d"))]`,
        },
        {
            tree: condition("foo", "next", [1, "b", "date"], true),
            result: `["!", "&", ("foo", ">=", context_today().strftime("%Y-%m-%d")), ("foo", "<=", (context_today() + relativedelta(b = 1)).strftime("%Y-%m-%d"))]`,
        },
        {
            tree: condition("foo", "not_next", [1, "weeks", "date"]),
            result: `["|", ("foo", "<", context_today().strftime("%Y-%m-%d")), ("foo", ">", (context_today() + relativedelta(weeks = 1)).strftime("%Y-%m-%d"))]`,
        },
        {
            tree: condition("foo", "not_next", [1, "weeks", "date"], true),
            result: `["!", "|", ("foo", "<", context_today().strftime("%Y-%m-%d")), ("foo", ">", (context_today() + relativedelta(weeks = 1)).strftime("%Y-%m-%d"))]`,
        },
    ];
    for (const { tree, result } of toTest) {
        expect(domainFromTree(tree).replace(/[\s\n]+/g, "")).toBe(result.replace(/[\s\n]+/g, ""));
    }
});
