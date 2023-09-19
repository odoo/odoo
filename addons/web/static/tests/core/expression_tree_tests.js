/** @odoo-module **/

import { Expression } from "@web/core/domain_tree";
import {
    domainFromExpression,
    expressionFromDomain,
    expressionFromExpressionTree,
} from "@web/core/expression_tree";
import { parseExpr } from "@web/core/py_js/py";

QUnit.module("expression tree", {});

QUnit.test("expression to domain", function (assert) {
    const options = { getFieldDef: (name) => (name === "x" ? {} : null) };
    const toTest = [
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
            expression: `x`,
            result: `[("x", "!=", False)]`,
        },
        {
            expression: `not A`,
            result: `[(not A, "=", 1)]`,
        },
        {
            expression: `not x`,
            result: `[("x", "=", False)]`,
        },
        {
            expression: `not not A`,
            result: `[(bool(A), "=", 1)]`,
        },
        {
            expression: `y == 2`,
            result: `[(y, "=", 2)]`,
        },
        {
            expression: `not (y == 2)`,
            result: `[(y, "!=", 2)]`,
        },
        {
            expression: `x == 2`,
            result: `[("x", "=", 2)]`,
        },
        {
            expression: `not (x == 2)`,
            result: `[("x", "!=", 2)]`,
        },
        {
            expression: `2 == x`,
            result: `[("x", "=", 2)]`,
        },
        {
            expression: `not (2 == x)`,
            result: `[("x", "!=", 2)]`,
        },
        {
            expression: `x < 2`,
            result: `[("x", "<", 2)]`,
        },
        {
            expression: `not (x < 2)`,
            result: `[("x", ">=", 2)]`,
        },
        {
            expression: `2 < x`,
            result: `[("x", ">", 2)]`,
        },
        {
            expression: `not (2 < x)`,
            result: `[("x", "<=", 2)]`,
        },
        {
            expression: `not(y == 1)`,
            result: `[(y, "!=", 1)]`,
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
            result: `[(bool(a for a in [1]), "=", 1)]`,
        },
        {
            expression: `[a for a in [1] if a in [1, 2]]`,
            result: `[(bool(a for a in [1] if a in [1, 2]), "=", 1)]`,
        },
        {
            expression: `[a for a in x]`,
            result: `[(bool(a for a in x), "=", 1)]`,
        },
        {
            expression: `[a for a in x if a in [1, 2]]`,
            result: `[("x", "in", [1, 2])]`,
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
        assert.deepEqual(domainFromExpression(expression, { ...options, ...extraOptions }), result);
    }
});

QUnit.test("domain to expression", function (assert) {
    const options = {
        getFieldDef: (name) => (name === "x" ? {} : null),
    };
    const toTest = [
        {
            domain: `[(1, "=", 1)]`,
            result: `True`,
        },
        {
            domain: `[(0, "=", 1)]`, // useful?: not possible to produce this in interface (outside of debug input)
            result: `False`,
        },
        {
            domain: `[("A", "=", 1)]`,
            result: `bool("A")`,
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
        assert.deepEqual(expressionFromDomain(domain, { ...options, extraOptions }), result);
    }
});

QUnit.test("expressionTree to expression", function (assert) {
    const options = {
        getFieldDef: (name) => (name === "x" ? {} : null),
    };
    const toTest = [
        {
            expressionTree: {
                type: "condition",
                negate: false,
                path: "x",
                operator: "=",
                value: false,
            },
            result: `not x`,
        },
        // {
        //     expressionTree: {
        //         type: "condition",
        //         negate: false,
        //         path: "y",
        //         operator: "=",
        //         value: false,
        //     },
        //     result: `not y`,
        // },
        {
            expressionTree: {
                type: "condition",
                negate: false,
                path: "x",
                operator: "!=",
                value: false,
            },
            result: `x`,
        },
        // {
        //     expressionTree: {
        //         type: "condition",
        //         negate: false,
        //         path: "y",
        //         operator: "!=",
        //         value: false,
        //     },
        //     result: `bool(y)`,
        // },
        {
            expressionTree: {
                type: "condition",
                negate: false,
                path: "x",
                operator: "between",
                value: [1, 3],
            },
            result: `x >= 1 and x <= 3`,
        },
        {
            expressionTree: {
                type: "condition",
                negate: true,
                path: "x",
                operator: "between",
                value: [1, new Expression(parseExpr("uid"))],
            },
            result: `not ( x >= 1 and x <= uid )`,
        },
    ];
    for (const { expressionTree, result, extraOptions } of toTest) {
        assert.strictEqual(
            expressionFromExpressionTree(expressionTree, { ...options, ...extraOptions }),
            result
        );
    }
});
