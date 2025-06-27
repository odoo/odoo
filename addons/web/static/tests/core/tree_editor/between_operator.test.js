import { describe, expect, test } from "@odoo/hoot";

import { makeMockEnv } from "@web/../tests/web_test_helpers";

import { condition, connector, expression } from "@web/core/tree_editor/condition_tree";
import {
    eliminateVirtualOperators,
    introduceVirtualOperators,
} from "@web/core/tree_editor/virtual_operators";

describe.current.tags("headless");

const options = {
    getFieldDef: (name) => {
        if (name === "m2o") {
            return { type: "many2one" };
        }
        if (name === "m2o.int_2" || name === "int_1") {
            return { type: "integer" };
        }
        return null;
    },
};

test("between operator: introduction/elimination", async () => {
    await makeMockEnv();
    const toTest = [
        {
            tree_py: connector("&", [condition("int_1", ">=", 1), condition("int_1", "<=", 2)]),
            tree: condition("int_1", "between", [1, 2]),
        },
        {
            tree_py: connector(
                "&",
                [condition("int_1", ">=", 1), condition("int_1", "<=", 2)],
                true
            ),
            tree: condition("int_1", "between", [1, 2], true),
        },
        {
            tree_py: connector("&", [
                condition("m2o.int_2", ">=", 1),
                condition("m2o.int_2", "<=", 2),
            ]),
            tree: connector("&", [
                condition("m2o.int_2", ">=", 1),
                condition("m2o.int_2", "<=", 2),
            ]),
        },
        {
            tree_py: condition(
                "m2o",
                "any",
                connector("&", [condition("int_2", ">=", 1), condition("int_2", "<=", 2)])
            ),
            tree: condition("m2o.int_2", "between", [1, 2]),
        },
        {
            tree_py: condition(
                "m2o",
                "any",
                connector("&", [condition("int_2", ">=", 1), condition("int_2", "<=", 2)]),
                true
            ),
            tree: condition("m2o", "any", condition("int_2", "between", [1, 2]), true),
        },
        {
            tree_py: connector("&", [
                condition(expression("path"), ">=", 1),
                condition(expression("path"), "<=", 2),
            ]),
            tree: connector("&", [
                condition(expression("path"), ">=", 1),
                condition(expression("path"), "<=", 2),
            ]),
        },
        {
            tree_py: condition(
                "m2o",
                "any",
                connector("&", [
                    condition(expression("path"), ">=", 1),
                    condition(expression("path"), "<=", 2),
                ])
            ),
            tree: condition(
                "m2o",
                "any",
                connector("&", [
                    condition(expression("path"), ">=", 1),
                    condition(expression("path"), "<=", 2),
                ])
            ),
        },
    ];
    for (const { tree_py, tree } of toTest) {
        expect(introduceVirtualOperators(tree_py, options)).toEqual(tree);
        expect(eliminateVirtualOperators(tree)).toEqual(tree_py);
    }
});
