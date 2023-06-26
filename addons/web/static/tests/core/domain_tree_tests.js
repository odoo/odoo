/** @odoo-module **/

import { Expression, toDomain, toTree } from "@web/core/domain_tree";

QUnit.module("domain tree", {});

QUnit.test("toDomain", function (assert) {
    const toTest = [
        {
            tree: { type: "condition", negate: false, path: "foo", operator: "=", value: false },
            result: `[("foo", "=", False)]`,
        },
        {
            tree: { type: "condition", negate: true, path: "foo", operator: "=", value: false },
            result: `["!", ("foo", "=", False)]`,
        },
        {
            tree: { type: "condition", negate: false, path: "foo", operator: "=?", value: false },
            result: `[("foo", "=?", False)]`,
        },
        {
            tree: { type: "condition", negate: true, path: "foo", operator: "=?", value: false },
            result: `["!", ("foo", "=?", False)]`,
        },
        {
            tree: {
                type: "condition",
                negate: false,
                path: "foo",
                operator: "between",
                value: [1, 3],
            },
            result: `["&", ("foo", ">=", 1), ("foo", "<=", 3)]`,
        },
        {
            tree: {
                type: "condition",
                negate: true,
                path: "foo",
                operator: "between",
                value: [1, new Expression({ type: 5, value: "uid" })],
            },
            result: `["!", "&", ("foo", ">=", 1), ("foo", "<=", uid)]`,
        },
    ];
    for (const { tree, result } of toTest) {
        assert.strictEqual(toDomain(tree), result);
    }
});

QUnit.test("toDomain . toTree", function (assert) {
    const toTest = [
        {
            domain: `[("foo", "=", False)]`,
            result: `[("foo", "=", False)]`,
        },
        {
            domain: `[("foo", "=", false)]`,
            result: `[("foo", "=", False)]`,
        },
        {
            domain: `[("foo", "=", true)]`,
            result: `[("foo", "=", True)]`,
        },
        {
            domain: `["!", ("foo", "=", False)]`,
            result: `[("foo", "!=", False)]`,
        },
        {
            domain: `[("foo", "=?", False)]`,
            result: `[("foo", "=?", False)]`,
        },
        {
            domain: `["!", ("foo", "=?", False)]`,
            result: `["!", ("foo", "=?", False)]`,
        },
        {
            domain: `["&", ("foo", ">=", 1), ("foo", "<=", 3)]`,
            result: `["&", ("foo", ">=", 1), ("foo", "<=", 3)]`,
        },
        {
            domain: `["&", ("foo", ">=", 1), ("foo", "<=", uid)]`,
            result: `["&", ("foo", ">=", 1), ("foo", "<=", uid)]`,
        },
    ];
    for (const { domain, result } of toTest) {
        assert.deepEqual(toDomain(toTree(domain)), result);
    }
});
