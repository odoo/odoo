import { expect, test } from "@odoo/hoot";

import { complexCondition, condition, expression } from "@web/core/tree_editor/condition_tree";
import { expressionFromTree } from "@web/core/tree_editor/expression_from_tree";

test("expressionFromTree", () => {
    const options = {
        getFieldDef: (name) => {
            if (["foo", "bar"].includes(name)) {
                return { type: "any" }; // any field
            }
            if (["foo_ids", "bar_ids"].includes(name)) {
                return { type: "many2many" };
            }
            return null;
        },
    };
    const toTest = [
        {
            expressionTree: condition("foo", "=", false),
            result: `not foo`,
        },
        {
            expressionTree: condition("foo", "=", false, true),
            result: `foo`,
        },
        {
            expressionTree: condition("foo", "!=", false),
            result: `foo`,
        },
        {
            expressionTree: condition("foo", "!=", false, true),
            result: `not foo`,
        },
        {
            expressionTree: condition("y", "=", false),
            result: `not "y"`,
        },
        {
            expressionTree: condition("foo", "between", [1, 3]),
            result: `foo >= 1 and foo <= 3`,
        },
        {
            expressionTree: condition("foo", "between", [1, expression("uid")], true),
            result: `not ( foo >= 1 and foo <= uid )`,
        },
        {
            expressionTree: complexCondition("uid"),
            result: `uid`,
        },
        {
            expressionTree: condition("foo_ids", "in", []),
            result: `set(foo_ids).intersection([])`,
        },
        {
            expressionTree: condition("foo_ids", "in", [1]),
            result: `set(foo_ids).intersection([1])`,
        },
        {
            expressionTree: condition("foo_ids", "in", 1),
            result: `set(foo_ids).intersection([1])`,
        },
        {
            expressionTree: condition("foo", "in", []),
            result: `foo in []`,
        },
        {
            expressionTree: condition(expression("expr"), "in", []),
            result: `expr in []`,
        },
        {
            expressionTree: condition("foo", "in", [1]),
            result: `foo in [1]`,
        },
        {
            expressionTree: condition("foo", "in", 1),
            result: `foo in [1]`,
        },
        {
            expressionTree: condition("foo", "in", expression("expr")),
            result: `foo in expr`,
        },
        {
            expressionTree: condition("foo_ids", "in", expression("expr")),
            result: `set(foo_ids).intersection(expr)`,
        },
        {
            expressionTree: condition("y", "in", []),
            result: `"y" in []`,
        },
        {
            expressionTree: condition("y", "in", [1]),
            result: `"y" in [1]`,
        },
        {
            expressionTree: condition("y", "in", 1),
            result: `"y" in [1]`,
        },
        {
            expressionTree: condition("foo_ids", "not in", []),
            result: `not set(foo_ids).intersection([])`,
        },
        {
            expressionTree: condition("foo_ids", "not in", [1]),
            result: `not set(foo_ids).intersection([1])`,
        },
        {
            expressionTree: condition("foo_ids", "not in", 1),
            result: `not set(foo_ids).intersection([1])`,
        },
        {
            expressionTree: condition("foo", "not in", []),
            result: `foo not in []`,
        },
        {
            expressionTree: condition("foo", "not in", [1]),
            result: `foo not in [1]`,
        },
        {
            expressionTree: condition("foo", "not in", 1),
            result: `foo not in [1]`,
        },
        {
            expressionTree: condition("y", "not in", []),
            result: `"y" not in []`,
        },
        {
            expressionTree: condition("y", "not in", [1]),
            result: `"y" not in [1]`,
        },
        {
            expressionTree: condition("y", "not in", 1),
            result: `"y" not in [1]`,
        },
    ];
    for (const { expressionTree, result, extraOptions } of toTest) {
        const o = { ...options, ...extraOptions };
        expect(expressionFromTree(expressionTree, o)).toBe(result);
    }
});
