/** @odoo-module **/

import {
    domainFromExpression,
    domainFromTree,
    Expression,
    expressionFromDomain,
    expressionFromTree,
    treeFromDomain,
    treeFromExpression,
} from "@web/core/tree_editor/condition_tree";

QUnit.module("condition tree", {});

QUnit.test("domainFromTree", function (assert) {
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
        assert.strictEqual(domainFromTree(tree), result);
    }
});

QUnit.test("domainFromTree . treeFromDomain", function (assert) {
    const toTest = [
        {
            domain: `[("foo", "=", False)]`,
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
        assert.deepEqual(domainFromTree(treeFromDomain(domain)), result);
    }
});

QUnit.test("domainFromExpression", function (assert) {
    const options = {
        getFieldDef: (name) => {
            if (["foo", "bar"].includes(name)) {
                return {}; // any field
            }
            if (name === "foo_ids") {
                return { type: "many2many" };
            }
            return null;
        },
    };
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
            result: `[(bool(foo is True), "=", 1)]`,
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
            expression: `foo >= 1 if foo else foo <= uid`,
            result: `["|", "&", ("foo", "!=", False), ("foo", ">=", 1), "&", ("foo", "=", False), ("foo", "<=", uid)]`,
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
        {
            expression: `True`,
            result: `[(1, "=", 1)]`,
        },
        {
            expression: `False`,
            result: `[(0, "=", 1)]`,
        },
        {
            expression: `A`,
            result: `[(bool(A), "=", 1)]`,
        },
        {
            expression: `foo`,
            result: `[("foo", "!=", False)]`,
        },
        {
            expression: `not A`,
            result: `[(not A, "=", 1)]`,
        },
        {
            expression: `not not A`,
            result: `[(bool(A), "=", 1)]`,
        },
        {
            expression: `y == 2`,
            result: `[(bool(y == 2), "=", 1)]`,
        },
        {
            expression: `not (y == 2)`,
            result: `[(bool(y != 2), "=", 1)]`,
        },
        {
            expression: `foo == 2`,
            result: `[("foo", "=", 2)]`,
        },
        {
            expression: `not (foo == 2)`,
            result: `[("foo", "!=", 2)]`,
        },
        {
            expression: `2 == foo`,
            result: `[("foo", "=", 2)]`,
        },
        {
            expression: `not (2 == foo)`,
            result: `[("foo", "!=", 2)]`,
        },
        {
            expression: `foo < 2`,
            result: `[("foo", "<", 2)]`,
        },
        {
            expression: `not (foo < 2)`,
            result: `[("foo", ">=", 2)]`,
        },
        {
            expression: `2 < foo`,
            result: `[("foo", ">", 2)]`,
        },
        {
            expression: `not (2 < foo)`,
            result: `[("foo", "<=", 2)]`,
        },
        {
            expression: `not(y == 1)`,
            result: `[(bool(y != 1), "=", 1)]`,
        },
        {
            expression: `A if B else C`,
            result: `["|", "&", (bool(B), "=", 1), (bool(A), "=", 1), "&", (not B, "=", 1), (bool(C), "=", 1)]`,
        },
        {
            expression: `not bool(A)`,
            result: `[(not A, "=", 1)]`,
        },
        {
            expression: `[a for a in [1]]`,
            result: `[(bool([a for a in [1]]), "=", 1)]`,
        },
        {
            expression: `[a for a in [1] if a in [1, 2]]`,
            result: `[(bool([a for a in [1] if a in [1, 2]]), "=", 1)]`,
        },
        {
            expression: `[a for a in foo]`,
            result: `[(bool([a for a in foo]), "=", 1)]`,
        },
        {
            expression: `[a for a in foo_ids if a in [1, 2]]`,
            result: `[("foo_ids", "in", [1, 2])]`,
        },
        {
            expression: `not(A and not B)`,
            result: `["!", "&", (bool(A), "=", 1), (not B, "=", 1)]`,
        },
        {
            expression: `not (A and not B)`,
            result: `["|", (not A, "=", 1), (bool(B), "=", 1)]`,
            extraOptions: { distributeNot: true },
        },
    ];
    for (const { expression, result, extraOptions } of toTest) {
        const o = { ...options, ...extraOptions };
        assert.deepEqual(domainFromExpression(expression, o), result);
    }
});

QUnit.test("expressionFromTree", function (assert) {
    const options = {
        getFieldDef: (name) => (name === "x" ? {} /** any field */ : null),
    };
    const toTest = [
        {
            expressionTree: {
                type: "condition",
                path: "x",
                negate: false,
                operator: "=",
                value: false,
            },
            result: `not x`,
        },
        {
            expressionTree: {
                type: "condition",
                path: "x",
                negate: true,
                operator: "=",
                value: false,
            },
            result: `x`,
        },
        {
            expressionTree: {
                type: "condition",
                path: "x",
                negate: false,
                operator: "!=",
                value: false,
            },
            result: `x`,
        },
        {
            expressionTree: {
                type: "condition",
                path: "x",
                negate: true,
                operator: "!=",
                value: false,
            },
            result: `not x`,
        },
        {
            expressionTree: {
                type: "condition",
                path: "y",
                negate: false,
                operator: "=",
                value: false,
            },
            result: `not "y"`,
        },
        {
            expressionTree: {
                type: "condition",
                path: "x",
                negate: false,
                operator: "between",
                value: [1, 3],
            },
            result: `x >= 1 and x <= 3`,
        },
        {
            expressionTree: {
                type: "condition",
                path: "x",
                negate: true,
                operator: "between",
                value: [1, new Expression("uid")],
            },
            result: `not ( x >= 1 and x <= uid )`,
        },
        {
            expressionTree: {
                type: "complex_condition",
                value: "uid",
            },
            result: `uid`,
        },
    ];
    for (const { expressionTree, result, extraOptions } of toTest) {
        const o = { ...options, ...extraOptions };
        assert.strictEqual(expressionFromTree(expressionTree, o), result);
    }
});

QUnit.test("treeFromExpression", function (assert) {
    const options = {
        getFieldDef: (name) => {
            if (["foo", "bar"].includes(name)) {
                return {}; // any field
            }
            if (name === "foo_ids") {
                return { type: "many2many" };
            }
            return null;
        },
    };
    const toTest = [
        {
            expression: `not foo`,
            result: {
                type: "condition",
                path: "foo",
                negate: false,
                operator: "not_set",
                value: false,
            },
        },
        {
            expression: `foo == False`,
            result: {
                type: "condition",
                path: "foo",
                operator: "not_set",
                negate: false,
                value: false,
            },
        },
        {
            expression: `foo`,
            result: {
                type: "condition",
                path: "foo",
                negate: false,
                operator: "set",
                value: false,
            },
        },
        {
            expression: `foo == True`,
            result: {
                type: "condition",
                path: "foo",
                negate: false,
                operator: "=",
                value: true,
            },
        },
        {
            expression: `foo is True`,
            result: {
                type: "complex_condition",
                value: `foo is True`,
            },
        },
        {
            expression: `not (foo == False)`,
            result: {
                type: "condition",
                path: "foo",
                negate: false,
                operator: "set",
                value: false,
            },
        },
        {
            expression: `not (not foo)`,
            result: {
                type: "condition",
                path: "foo",
                negate: false,
                operator: "set",
                value: false,
            },
        },
        {
            expression: `foo >= 1 and foo <= 3`,
            result: {
                type: "condition",
                negate: false,
                operator: "between",
                path: "foo",
                value: [1, 3],
            },
        },
        {
            expression: `foo >= 1 and foo <= uid`,
            result: {
                type: "condition",
                path: "foo",
                negate: false,
                operator: "between",
                value: [1, new Expression("uid")],
            },
        },
        {
            expression: `foo >= 1 if bar else foo <= uid`,
            result: {
                type: "connector",
                negate: false,
                value: "|",
                children: [
                    {
                        type: "connector",
                        negate: false,
                        value: "&",
                        children: [
                            {
                                type: "condition",
                                path: "bar",
                                negate: false,
                                operator: "set",
                                value: false,
                            },
                            {
                                type: "condition",
                                path: "foo",
                                negate: false,
                                operator: ">=",
                                value: 1,
                            },
                        ],
                    },
                    {
                        type: "connector",
                        negate: false,
                        value: "&",
                        children: [
                            {
                                type: "condition",
                                path: "bar",
                                negate: false,
                                operator: "not_set",
                                value: false,
                            },
                            {
                                type: "condition",
                                path: "foo",
                                negate: false,
                                operator: "<=",
                                value: new Expression("uid"),
                            },
                        ],
                    },
                ],
            },
        },
        {
            expression: `context.get('toto')`,
            result: {
                type: "complex_condition",
                value: `context.get("toto")`,
            },
        },
        {
            expression: `not context.get('toto')`,
            result: {
                type: "complex_condition",
                value: `not context.get("toto")`,
            },
        },
        {
            expression: `foo >= 1 if context.get('toto') else bar == 42`,
            result: {
                type: "connector",
                negate: false,
                value: "|",
                children: [
                    {
                        type: "connector",
                        negate: false,
                        value: "&",
                        children: [
                            {
                                type: "complex_condition",
                                value: `context.get("toto")`,
                            },
                            {
                                type: "condition",
                                path: "foo",
                                negate: false,
                                operator: ">=",
                                value: 1,
                            },
                        ],
                    },
                    {
                        type: "connector",
                        negate: false,
                        value: "&",
                        children: [
                            {
                                type: "complex_condition",
                                value: `not context.get("toto")`,
                            },
                            {
                                type: "condition",
                                path: "bar",
                                negate: false,
                                operator: "=",
                                value: 42,
                            },
                        ],
                    },
                ],
            },
        },
        {
            expression: `[f(id) for id in foo_ids]`,
            result: {
                type: "complex_condition",
                value: `[f(id) for id in foo_ids]`,
            },
        },
        {
            expression: `[id for id in foo_ids if f(id) in [1, 2]]`,
            result: {
                type: "complex_condition",
                value: `[id for id in foo_ids if f(id) in [1, 2]]`,
            },
        },
        {
            expression: `[id for id in foo_ids if id in [2,uid]]`,
            result: {
                type: "condition",
                path: "foo_ids",
                negate: false,
                operator: "in",
                value: [2, new Expression("uid")],
            },
        },
        {
            expression: `[id for id in foo_ids if id not in [2,uid]]`,
            result: {
                type: "condition",
                path: "foo_ids",
                negate: false,
                operator: "not in",
                value: [2, new Expression("uid")],
            },
        },
        {
            expression: `[id for id in [2, uid] if id in foo_ids]`,
            result: {
                type: "condition",
                path: "foo_ids",
                negate: false,
                operator: "in",
                value: [2, new Expression("uid")],
            },
        },
        {
            expression: `[id for id in [2, uid] if id not in foo_ids]`,
            result: {
                type: "complex_condition",
                value: `[id for id in [2, uid] if id not in foo_ids]`,
            },
        },
        {
            expression: `[id in [2, uid] for id in foo_ids]`,
            result: {
                type: "condition",
                path: "foo_ids",
                negate: false,
                operator: "in",
                value: [2, new Expression("uid")],
            },
        },
        {
            expression: `[id not in [2, uid] for id in foo_ids]`,
            result: {
                type: "condition",
                path: "foo_ids",
                negate: false,
                operator: "not in",
                value: [2, new Expression("uid")],
            },
        },
        {
            expression: `[id in foo_ids for id in [2, uid]]`,
            result: {
                type: "condition",
                path: "foo_ids",
                negate: false,
                operator: "in",
                value: [2, new Expression("uid")],
            },
        },
        {
            expression: `[id not in foo_ids for id in [2, uid]]`,
            result: {
                type: "complex_condition",
                value: `[id not in foo_ids for id in [2, uid]]`,
            },
        },
        {
            expression: `any([id for id in foo_ids if id in [2,uid]])`,
            result: {
                type: "condition",
                path: "foo_ids",
                negate: false,
                operator: "in",
                value: [2, new Expression("uid")],
            },
        },
        {
            expression: `any([id for id in foo_ids if id not in [2,uid]])`,
            result: {
                type: "condition",
                path: "foo_ids",
                negate: false,
                operator: "not in",
                value: [2, new Expression("uid")],
            },
        },
        {
            expression: `any([id for id in [2, uid] if id in foo_ids])`,
            result: {
                type: "condition",
                path: "foo_ids",
                negate: false,
                operator: "in",
                value: [2, new Expression("uid")],
            },
        },
        // TODO: improvement: get conditions for the expressions below
        {
            expression: `all(id for id in foo_ids if (id in [2,4]))`,
            result: {
                type: "complex_condition",
                value: "all([id for id in foo_ids if id in [2, 4]])",
            },
        },
        {
            expression: `all(id in [2,4] for (id in foo_ids))`,
            result: {
                type: "complex_condition",
                value: "all([id for (,id,in,foo_ids in id in foo_ids if id in [2, 4]])",
            },
        },
        {
            expression: `not any(id not in [2,4] for id in foo_ids)`,
            result: {
                type: "complex_condition",
                value: "all([id in [2, 4] for id in foo_ids])",
            },
        },
    ];
    for (const { expression, result, extraOptions } of toTest) {
        const o = { ...options, ...extraOptions };
        assert.deepEqual(treeFromExpression(expression, o), result);
    }
});

QUnit.test("expressionFromTree . treeFromExpression", function (assert) {
    const options = {
        getFieldDef: (name) => {
            if (["foo", "bar"].includes(name)) {
                return {}; // any field
            }
            if (name === "foo_ids") {
                return { type: "many2many" };
            }
            return null;
        },
    };
    const toTest = [
        {
            expression: `not foo`,
            result: `not foo`,
        },
        {
            expression: `foo == False`,
            result: `not foo`,
        },
        {
            expression: `foo == None`,
            result: `foo == None`,
        },
        {
            expression: `foo is None`,
            result: `foo is None`,
        },
        {
            expression: `foo`,
            result: `foo`,
        },
        {
            expression: `foo == True`,
            result: `foo == True`,
        },
        {
            expression: `foo is True`,
            result: `foo is True`,
        },
        {
            expression: `not (foo == False)`,
            result: `foo`,
        },
        {
            expression: `not (not foo)`,
            result: `foo`,
        },
        {
            expression: `foo >= 1 and foo <= 3`,
            result: `foo >= 1 and foo <= 3`,
        },
        {
            expression: `foo >= 1 and foo <= uid`,
            result: `foo >= 1 and foo <= uid`,
        },
        {
            expression: `foo >= 1 if glob else foo <= uid`,
            result: `foo >= 1 if glob else foo <= uid`,
        },
        {
            expression: `context.get("toto")`,
            result: `context.get("toto")`,
        },
        {
            expression: `foo >= 1 if context.get("toto") else bar == 42`,
            result: `foo >= 1 if context.get("toto") else bar == 42`,
        },
        {
            expression: `not context.get("toto")`,
            result: `not context.get("toto")`,
        },
        {
            expression: `any(id in [2,4] for id in foo_ids)`,
            result: `foo_ids in [2, 4]`,
        },
        {
            expression: `[id for id in foo_ids if id in [2,4]]`,
            result: `foo_ids in [2, 4]`, // because it's a boolean expression
        },
        {
            expression: `any(id for id in foo_ids if (id in [2,4]))`,
            result: `foo_ids in [2, 4]`,
        },
        {
            expression: `all(id in [2,4] for id in foo_ids)`,
            result: `all([id for id in foo_ids if id in [2, 4]])`,
        },
        {
            expression: `not any(id not in [2,4] for id in foo_ids)`,
            result: `all([id in [2, 4] for id in foo_ids])`,
        },
    ];
    for (const { expression, result, extraOptions } of toTest) {
        const o = { ...options, ...extraOptions };
        assert.deepEqual(expressionFromTree(treeFromExpression(expression, o), o), result);
    }
});

QUnit.test("expressionFromDomain", function (assert) {
    const options = {
        getFieldDef: (name) => (name === "x" ? {} : null),
    };
    const toTest = [
        {
            domain: `[(1, "=", 1)]`,
            result: `True`,
        },
        {
            domain: `[(0, "=", 1)]`,
            result: `False`,
        },
        {
            domain: `[("A", "=", 1)]`,
            result: `"A" == 1`,
        },
        {
            domain: `[(bool(A), "=", 1)]`,
            result: `bool(A)`,
        },
        {
            domain: `[("x", "=", 2)]`,
            result: `x == 2`,
        },
    ];

    for (const { domain, result, extraOptions } of toTest) {
        const o = { ...options, ...extraOptions };
        assert.deepEqual(expressionFromDomain(domain, o), result);
    }
});
