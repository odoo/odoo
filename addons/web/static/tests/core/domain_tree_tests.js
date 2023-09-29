/** @odoo-module **/

import { Expression, toDomain, toTree, toExpression, expressionToTree } from "@web/core/domain_tree";

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

QUnit.test("toExpression", function (assert) {
    const toTest = [
        {
            tree: { type: "condition", negate: false, path: "foo", operator: "=", value: false },
            result: `foo == False`,
        },
        {
            tree: { type: "condition", negate: true, path: "foo", operator: "=", value: false },
            result: `not (foo == False)`,
        },
        {
            tree: {
                type: "condition",
                negate: false,
                path: "foo",
                operator: "between",
                value: [1, 3],
            },
            result: `foo >= 1 and foo <= 3`,
        },
        {
            tree: {
                type: "condition",
                negate: true,
                path: "foo",
                operator: "between",
                value: [1, new Expression({ type: 5, value: "uid" })],
            },
            result: `not (foo >= 1 and foo <= uid)`,
        },
    ];
    for (const { tree, result } of toTest) {
        assert.strictEqual(toExpression(tree), result);
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

QUnit.test("toDomain . expressionToTree", function (assert) {

    const toTest = [
        {
            expression: `not foo`,
            result: `[("foo", "=", False)]`,
        },
        {
            expression: `foo == False`,
            result: `[("foo", "=", False)]`,
        },
        {
            expression: `foo`,
            result: `[("foo", "!=", False)]`,
        },
        {
            expression: `foo == True`,
            result: `[("foo", "=", True)]`,
        },
        {
            expression: `foo is True`,
            result: `[("foo", "=", True)]`,
        },
        {
            expression: `not (foo == False)`,
            result: `[("foo", "!=", False)]`,
        },
        {
            expression: `not (not foo)`,
            result: `[("foo", "!=", False)]`,
        },
        {
            expression: `foo >= 1 and foo <= 3`,
            result: `["&", ("foo", ">=", 1), ("foo", "<=", 3)]`,
        },
        {
            expression: `foo >= 1 and foo <= uid`,
            result: `["&", ("foo", ">=", 1), ("foo", "<=", uid)]`,
        },
        {
            expression: `foo >= 1 if glob else foo <= uid`,
            result: `["|", "&", ("glob", "!=", False), ("foo", ">=", 1), "&", "!", ("glob", "!=", False), ("foo", "<=", uid)]`,
        },
        {
            expression: `context.get('toto')`,
            result: `[(bool(context.get("toto")), "=", 1)]`,
        },
        {
            expression: `foo >= 1 if context.get('toto') else bar == 42`,
            result: `["|", "&", (bool(context.get("toto")), "=", 1), ("foo", ">=", 1), "&", (not context.get("toto"), "=", 1), ("bar", "=", 42)]`,
        },
        {
            expression: `not context.get('toto')`,
            result: `[(not context.get("toto"), "=", 1)]`,
        },
        {
            expression: `any(id for id in foo_ids if (id in [2,4]))`,
            result: `[("foo_ids", "in", [2, 4])]`,
        },
        {
            expression: `[id for id in foo_ids if id in [2,4]]`,
            result: `[("foo_ids", "in", [2, 4])]`,
        },
    ];
    for (const { expression, result } of toTest) {
        assert.deepEqual(toDomain(expressionToTree(expression)), result);
    }
});
