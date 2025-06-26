import { expect, test } from "@odoo/hoot";

import { formatDomain } from "./condition_tree_editor_test_helpers";

import { condition, connector } from "@web/core/tree_editor/condition_tree";
import { constructDomainFromTree } from "@web/core/tree_editor/construct_domain_from_tree";

test("constructDomainFromTree", async () => {
    const toTest = [
        { tree: connector("&"), domain: `[]` },
        { tree: connector("&", [], true), domain: `[(0, "=", 1)]` },
        { tree: connector("|"), domain: `[(0, "=", 1)]` },
        { tree: connector("|", [], true), domain: `[(1, "=", 1)]` },
        { tree: condition(1, "=", 1), domain: `[(1, "=", 1)]` },
        { tree: condition(0, "=", 1), domain: `[(0, "=", 1)]` },
        { tree: condition(1, "=", 1, true), domain: `["!", (1, "=", 1)]` },
        { tree: condition(0, "=", 1, true), domain: `["!", (0, "=", 1)]` },
        { tree: connector("|", [connector("|")]), domain: `[(0, "=", 1)]` },
        { tree: connector("|", [connector("&")]), domain: `[(1, "=", 1)]` },
        { tree: connector("&", [connector("&")]), domain: `[(1, "=", 1)]` },
        { tree: connector("&", [connector("|")]), domain: `[(0, "=", 1)]` },
        {
            tree: connector("|", [connector("|"), condition("id", "=", 1)]),
            domain: `["|", (0, "=", 1), ("id", "=", 1)]`,
        },
        {
            tree: connector("|", [connector("&"), condition("id", "=", 1)]),
            domain: `["|", (1, "=", 1), ("id", "=", 1)]`,
        },
        {
            tree: connector("&", [connector("&"), condition("id", "=", 1)]),
            domain: `["&", (1, "=", 1), ("id", "=", 1)]`,
        },
        {
            tree: connector("&", [connector("|"), condition("id", "=", 1)]),
            domain: `["&", (0, "=", 1), ("id", "=", 1)]`,
        },
        {
            tree: condition("id", "=", 1),
            domain: `[("id", "=", 1)]`,
        },
        {
            tree: condition("m2m", "any", connector("&")),
            domain: `[("m2m", "any", [])]`,
        },
        {
            tree: condition("m2m", "any", connector("&", [connector("&")])),
            domain: `[("m2m", "any", [(1, "=", 1)])]`,
        },
        {
            tree: condition("m2m", "any", connector("&", [connector("|")])),
            domain: `[("m2m", "any", [(0, "=", 1)])]`,
        },
        {
            tree: condition("m2m", "any", connector("|", [connector("|")])),
            domain: `[("m2m", "any", [(0, "=", 1)])]`,
        },
        {
            tree: condition("m2m", "any", connector("|", [connector("&")])),
            domain: `[("m2m", "any", [(1, "=", 1)])]`,
        },
    ];
    for (const { tree, domain } of toTest) {
        expect(constructDomainFromTree(tree)).toBe(formatDomain(domain));
    }
});
