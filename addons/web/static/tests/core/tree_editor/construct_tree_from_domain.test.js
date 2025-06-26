import { expect, test } from "@odoo/hoot";

import { condition, connector } from "@web/core/tree_editor/condition_tree";
import { constructTreeFromDomain } from "@web/core/tree_editor/construct_tree_from_domain";

test("constructTreeFromDomain", async () => {
    const toTest = [
        { domain: `[]`, tree: connector("&") },
        { domain: `[(0, "=", 1)]`, tree: condition(0, "=", 1) },
        { domain: `[(1, "=", 1)]`, tree: condition(1, "=", 1) },
        { domain: `["!", (0, "=", 1)]`, tree: condition(0, "=", 1, true) },
        { domain: `["!", (1, "=", 1)]`, tree: condition(1, "=", 1, true) },
    ];
    for (const { domain, tree } of toTest) {
        expect(constructTreeFromDomain(domain)).toEqual(tree);
    }
});
