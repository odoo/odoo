import { expect, test } from "@odoo/hoot";

import { makeMockEnv } from "@web/../tests/web_test_helpers";

import { condition } from "@web/core/tree_editor/condition_tree";
import { domainFromTree } from "@web/core/tree_editor/domain_from_tree";

test("domainFromTree", async () => {
    await makeMockEnv();
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
            tree: condition("foo", "starts with", "hello"),
            result: `[("foo", "=ilike", "hello%")]`,
        },
    ];
    for (const { tree, result } of toTest) {
        expect(domainFromTree(tree).replace(/[\s\n]+/g, "")).toBe(result.replace(/[\s\n]+/g, ""));
    }
});
