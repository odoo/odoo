import { describe, expect, test } from "@odoo/hoot";

import { makeMockEnv } from "@web/../tests/web_test_helpers";

import { Domain } from "@web/core/domain";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { condition, expression } from "@web/core/tree_editor/condition_tree";
import { constructDomainFromTree } from "@web/core/tree_editor/construct_domain_from_tree";
import { constructExpressionFromTree } from "@web/core/tree_editor/construct_expression_from_tree";
import { constructTreeFromDomain } from "@web/core/tree_editor/construct_tree_from_domain";
import { constructTreeFromExpression } from "@web/core/tree_editor/construct_tree_from_expression";
import { domainFromTree } from "@web/core/tree_editor/domain_from_tree";
import { expressionFromTree } from "@web/core/tree_editor/expression_from_tree";
import { treeFromExpression } from "@web/core/tree_editor/tree_from_expression";

function expressionFromDomain(domain, options) {
    const tree = constructTreeFromDomain(domain);
    return constructExpressionFromTree(tree, options);
}

function domainFromExpression(expression, options) {
    const tree = constructTreeFromExpression(expression, options);
    return constructDomainFromTree(tree);
}

describe.current.tags("headless");

test("constructDomainFromTree . constructTreeFromDomain", async () => {
    await makeMockEnv();
    const toTest = [
        {
            domain: `[("foo", "=", False)]`,
        },
        {
            domain: `[("foo", "=", true)]`,
            result: `[("foo", "=", True)]`,
        },
        {
            domain: `["!", ("foo", "=", False)]`,
            result: `["!", ("foo", "=", False)]`,
        },
        {
            domain: `[("foo", "=?", False)]`,
        },
        {
            domain: `["!", ("foo", "=?", False)]`,
        },
        {
            domain: `[("foo", "=ilike", "%hello")]`,
        },
        {
            domain: `["&", ("foo", ">=", 1), ("foo", "<=", 3)]`,
        },
        {
            domain: `["&", ("foo", ">=", 1), ("foo", "<=", uid)]`,
        },
        {
            domain: `["&", ("foo", ">=", context_today().strftime("%Y-%m-%d")), ("foo", "<=", (context_today() + relativedelta(weeks = 1)).strftime("%Y-%m-%d"))]`,
        },
        {
            domain: `["&", ("foo", ">=", datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")), ("foo", "<=", datetime.datetime.combine(context_today() + relativedelta(months = 1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S"))]`,
        },
        {
            domain: `["!", "&", ("foo", ">=", 1), ("foo", "<=", uid)]`,
        },
        {
            domain: `["!", "|", ("foo", "<", 1), ("foo", ">", uid)]`,
        },
    ];
    for (const { domain, result } of toTest) {
        expect(constructDomainFromTree(constructTreeFromDomain(domain))).toBe(result || domain);
    }
});

test("domainFromExpression", () => {
    const options = {
        getFieldDef: (name) => {
            if (["foo", "bar"].includes(name)) {
                return { type: "any" }; // any field
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
        expect(domainFromExpression(expression, o)).toBe(result);
    }
});

test("expressionFromTree . treeFromExpression", () => {
    const options = {
        getFieldDef: (name) => {
            if (["foo", "bar"].includes(name)) {
                return { type: "any" }; // any field
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
            expression: `set()`,
            result: `set()`,
        },
        {
            expression: `set([1, 2])`,
            result: `set([1, 2])`,
        },
        {
            expression: `set(foo_ids).intersection([1, 2])`,
            result: `set(foo_ids).intersection([1, 2])`,
        },
        {
            expression: `set(foo_ids).intersection(set([1, 2]))`,
            result: `set(foo_ids).intersection([1, 2])`,
        },
        {
            expression: `set(foo_ids).intersection(set((1, 2)))`,
            result: `set(foo_ids).intersection([1, 2])`,
        },
        {
            expression: `set(foo_ids).intersection("ab")`,
            result: `set(foo_ids).intersection("ab")`,
        },
        {
            expression: `set([1, 2]).intersection(foo_ids)`,
            result: `set(foo_ids).intersection([1, 2])`,
        },
        {
            expression: `set(set([1, 2])).intersection(foo_ids)`,
            result: `set(foo_ids).intersection([1, 2])`,
        },
        {
            expression: `set((1, 2)).intersection(foo_ids)`,
            result: `set(foo_ids).intersection([1, 2])`,
        },
        {
            expression: `set("ab").intersection(foo_ids)`,
            result: `set("ab").intersection(foo_ids)`,
        },
        {
            expression: `set([2, 3]).intersection([1, 2])`,
            result: `set([2, 3]).intersection([1, 2])`,
        },
        {
            expression: `set(foo_ids).intersection(bar_ids)`,
            result: `set(foo_ids).intersection(bar_ids)`,
        },
        {
            expression: `set().intersection(foo_ids)`,
            result: `False`,
        },
        {
            expression: `set(foo_ids).intersection()`,
            result: `foo_ids`,
        },
        {
            expression: `not set(foo_ids).intersection([1, 2])`,
            result: `not set(foo_ids).intersection([1, 2])`,
        },
        {
            expression: `not set(foo_ids).intersection(set([1, 2]))`,
            result: `not set(foo_ids).intersection([1, 2])`,
        },
        {
            expression: `not set(foo_ids).intersection(set((1, 2)))`,
            result: `not set(foo_ids).intersection([1, 2])`,
        },
        {
            expression: `not set(foo_ids).intersection("ab")`,
            result: `not set(foo_ids).intersection("ab")`,
        },
        {
            expression: `not set([1, 2]).intersection(foo_ids)`,
            result: `not set(foo_ids).intersection([1, 2])`,
        },
        {
            expression: `not set(set([1, 2])).intersection(foo_ids)`,
            result: `not set(foo_ids).intersection([1, 2])`,
        },
        {
            expression: `not set((1, 2)).intersection(foo_ids)`,
            result: `not set(foo_ids).intersection([1, 2])`,
        },
        {
            expression: `not set("ab").intersection(foo_ids)`,
            result: `not set("ab").intersection(foo_ids)`,
        },
        {
            expression: `not set([2, 3]).intersection([1, 2])`,
            result: `not set([2, 3]).intersection([1, 2])`,
        },
        {
            expression: `not set(foo_ids).intersection(bar_ids)`,
            result: `not set(foo_ids).intersection(bar_ids)`,
        },
        {
            expression: `set(foo_ids).difference([1, 2])`,
            result: `set(foo_ids).difference([1, 2])`,
        },
        {
            expression: `set(foo_ids).intersection([1, 2])`,
            result: `set(foo_ids).intersection([1, 2])`,
        },
        {
            expression: `set([foo]).intersection()`,
            result: `foo`,
        },
        {
            expression: `set([foo]).intersection([1, 2])`,
            result: `foo in [1, 2]`,
        },
        {
            expression: `set().intersection([foo])`,
            result: `False`,
        },
        {
            expression: `set([1, 2]).intersection([foo])`,
            result: `foo in [1, 2]`,
        },
        {
            expression: `not set([foo]).intersection()`,
            result: `not foo`,
        },
        {
            expression: `not set([foo]).intersection([1, 2])`,
            result: `foo not in [1, 2]`,
        },
        {
            expression: `not set().intersection([foo])`,
            result: `True`,
        },
        {
            expression: `not set([1, 2]).intersection([foo])`,
            result: `foo not in [1, 2]`,
        },
    ];
    for (const { expression, result, extraOptions } of toTest) {
        const o = { ...options, ...extraOptions };
        expect(expressionFromTree(treeFromExpression(expression, o), o)).toBe(result);
    }
});

test("expressionFromDomain", () => {
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
        expect(expressionFromDomain(domain, o)).toBe(result);
    }
});

test("evaluation . expressionFromTree = contains . domainFromTree", () => {
    const options = {
        getFieldDef: (name) => {
            if (name === "foo") {
                return { type: "any" }; // any field
            }
            if (name === "foo_ids") {
                return { type: "many2many" };
            }
            if (name === "date_field") {
                return { type: "date" };
            }
            if (name === "datetime_field") {
                return { type: "datetime" };
            }
            return null;
        },
    };

    const record = {
        foo: 1,
        foo_ids: [1, 2],
        uid: 7,
        expr: "abc",
        expr2: [1],
        datefield: "2024-02-05 00:00:00",
        datetimefield: "2024-02-05",
    };

    const toTest = [
        condition("foo", "=", false),
        condition("foo", "=", false, true),
        condition("foo", "!=", false),
        condition("foo", "!=", false, true),
        condition("y", "=", false),
        condition("foo", "between", [1, 3]),
        condition("foo", "between", [1, expression("uid")], true),
        condition("foo_ids", "in", []),
        condition("foo_ids", "in", [1]),
        condition("foo_ids", "in", 1),
        condition("foo", "in", []),
        condition(expression("expr"), "in", []),
        condition("foo", "in", [1]),
        condition("foo", "in", 1),
        condition("y", "in", []),
        condition("y", "in", [1]),
        condition("y", "in", 1),
        condition("foo_ids", "not in", []),
        condition("foo_ids", "not in", [1]),
        condition("foo_ids", "not in", 1),
        condition("foo", "not in", []),
        condition("foo", "not in", [1]),
        condition("foo", "not in", 1),
        condition("y", "not in", []),
        condition("y", "not in", [1]),
        condition("y", "not in", 1),
        condition("foo", "in", expression("expr2")),
        condition("foo_ids", "in", expression("expr2")),
    ];
    for (const tree of toTest) {
        expect(evaluateBooleanExpr(expressionFromTree(tree, options), record)).toBe(
            new Domain(domainFromTree(tree)).contains(record)
        );
    }
});
