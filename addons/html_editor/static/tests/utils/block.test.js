import { closestBlock } from "@html_editor/utils/blocks";
import { isVisibleTextNode } from "@html_editor/utils/dom_info";
import { describe, expect, test } from "@odoo/hoot";
import { insertTestHtml } from "../_helpers/editor";

describe("closestBlock", () => {
    test("should find the closest block of a deeply nested text node", () => {
        const [div] = insertTestHtml("<div><div><p>ab<b><i><u>cd</u></i></b>ef</p></div></div>");
        const p = div.firstChild.firstChild;
        const cd = p.childNodes[1].firstChild.firstChild.firstChild;
        const result = closestBlock(cd);
        expect(result).toBe(p);
    });

    test("should find that the closest block to a block is itself", () => {
        const [div] = insertTestHtml("<div><div><p>ab</p></div></div>");
        const p = div.firstChild.firstChild;
        const result = closestBlock(p);
        expect(result).toBe(p);
    });

    test("should return null if no block ancestor", () => {
        const node = document.createTextNode("\n        ");
        expect(closestBlock(node)).toBe(null);
        expect(isVisibleTextNode(node)).toBe(false);
    });
});
