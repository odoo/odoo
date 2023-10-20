/** @odoo-module **/

import {
    complexCondition,
    condition,
    connector,
    domainFromExpression,
    domainFromTree,
    expression,
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
            tree: condition("foo", "between", [1, 3]),
            result: `["&", ("foo", ">=", 1), ("foo", "<=", 3)]`,
        },
        {
            tree: condition("foo", "between", [1, expression("uid")], true),
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
            expressionTree: condition("x", "=", false),
            result: `not x`,
        },
        {
            expressionTree: condition("x", "=", false, true),
            result: `x`,
        },
        {
            expressionTree: condition("x", "!=", false),
            result: `x`,
        },
        {
            expressionTree: condition("x", "!=", false, true),
            result: `not x`,
        },
        {
            expressionTree: condition("y", "=", false),
            result: `not "y"`,
        },
        {
            expressionTree: condition("x", "between", [1, 3]),
            result: `x >= 1 and x <= 3`,
        },
        {
            expressionTree: condition("x", "between", [1, expression("uid")], true),
            result: `not ( x >= 1 and x <= uid )`,
        },
        {
            expressionTree: complexCondition("uid"),
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
            result: condition("foo", "not_set", false),
        },
        {
            expression: `foo == False`,
            result: condition("foo", "not_set", false),
        },
        {
            expression: `foo`,
            result: condition("foo", "set", false),
        },
        {
            expression: `foo == True`,
            result: condition("foo", "=", true),
        },
        {
            expression: `foo is True`,
            result: complexCondition(`foo is True`),
        },
        {
            expression: `not (foo == False)`,
            result: condition("foo", "set", false),
        },
        {
            expression: `not (not foo)`,
            result: condition("foo", "set", false),
        },
        {
            expression: `foo >= 1 and foo <= 3`,
            result: condition("foo", "between", [1, 3]),
        },
        {
            expression: `foo >= 1 and foo <= uid`,
            result: condition("foo", "between", [1, expression("uid")]),
        },
        {
            expression: `foo >= 1 if bar else foo <= uid`,
            result: connector("|", [
                connector("&", [condition("bar", "set", false), condition("foo", ">=", 1)]),
                connector("&", [
                    condition("bar", "not_set", false),
                    condition("foo", "<=", new Expression("uid")),
                ]),
            ]),
        },
        {
            expression: `context.get('toto')`,
            result: complexCondition(`context.get("toto")`),
        },
        {
            expression: `not context.get('toto')`,
            result: complexCondition(`not context.get("toto")`),
        },
        {
            expression: `foo >= 1 if context.get('toto') else bar == 42`,
            result: connector("|", [
                connector("&", [
                    complexCondition(`context.get("toto")`),
                    condition("foo", ">=", 1),
                ]),
                connector("&", [
                    complexCondition(`not context.get("toto")`),
                    condition("bar", "=", 42),
                ]),
            ]),
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
