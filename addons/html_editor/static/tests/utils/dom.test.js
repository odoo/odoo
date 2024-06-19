import { describe, expect, test } from "@odoo/hoot";
import { setupEditor } from "../_helpers/editor";
import { cleanTextNode } from "@html_editor/utils/dom";
import { getContent } from "../_helpers/selection";

describe("splitAroundUntil", () => {
    test("should split a slice of text from its inline ancestry (1)", async () => {
        const { editor, el } = await setupEditor("<p>a<font>b<span>cde</span>f</font>g</p>");
        const [p] = el.childNodes;
        const cde = p.childNodes[1].childNodes[1].firstChild;
        // We want to test with "cde" being three separate text nodes.
        editor.shared.splitTextNode(cde, 2);
        const cd = cde.previousSibling;
        editor.shared.splitTextNode(cd, 1);
        const d = cd;
        const result = editor.shared.splitAroundUntil(d, p.childNodes[1]);
        expect(result.tagName === "FONT").toBe(true);
        expect(p.outerHTML).toBe(
            "<p>a<font>b<span>c</span></font><font><span>d</span></font><font><span>e</span>f</font>g</p>"
        );
    });

    test("should split a slice of text from its inline ancestry (2)", async () => {
        const { editor, el } = await setupEditor("<p>a<font>b<span>cdefg</span>h</font>i</p>");
        const [p] = el.childNodes;
        const cdefg = p.childNodes[1].childNodes[1].firstChild;
        // We want to test with "cdefg" being five separate text nodes.
        editor.shared.splitTextNode(cdefg, 4);
        const cdef = cdefg.previousSibling;
        editor.shared.splitTextNode(cdef, 3);
        const cde = cdef.previousSibling;
        editor.shared.splitTextNode(cde, 2);
        const cd = cde.previousSibling;
        editor.shared.splitTextNode(cd, 1);
        const d = cd;
        const result = editor.shared.splitAroundUntil(
            [d, d.nextSibling.nextSibling],
            p.childNodes[1]
        );
        expect(result.tagName === "FONT").toBe(true);
        expect(p.outerHTML).toBe(
            "<p>a<font>b<span>c</span></font><font><span>def</span></font><font><span>g</span>h</font>i</p>"
        );
    });

    test("should split from a textNode that has no siblings", async () => {
        const { editor, el } = await setupEditor("<p>a<font>b<span>cde</span>f</font>g</p>");
        const [p] = el.childNodes;
        const font = p.querySelector("font");
        const cde = p.querySelector("span").firstChild;
        const result = editor.shared.splitAroundUntil(cde, font);
        expect(result.tagName === "FONT" && result !== font).toBe(true);
        expect(p.outerHTML).toBe(
            "<p>a<font>b</font><font><span>cde</span></font><font>f</font>g</p>"
        );
    });

    test("should not do anything (nothing to split)", async () => {
        const { editor, el } = await setupEditor("<p>a<font><span>bcd</span></font>e</p>");
        const [p] = el.childNodes;
        const bcd = p.querySelector("span").firstChild;
        const result = editor.shared.splitAroundUntil(bcd, p.childNodes[1]);
        expect(result === p.childNodes[1]).toBe(true);
        expect(p.outerHTML).toBe("<p>a<font><span>bcd</span></font>e</p>");
    });
});

describe("cleanTextNode", () => {
    test("should remove ZWS before cursor and preserve it", async () => {
        const { editor, el } = await setupEditor("<p>\u200B[]text</p>");
        const cursors = editor.shared.preserveSelection();
        cleanTextNode(el.querySelector("p").firstChild, "\u200B", cursors);
        cursors.restore();
        expect(getContent(el)).toBe("<p>[]text</p>");
    });
    test("should remove ZWS before cursor and preserve it (2)", async () => {
        const { editor, el } = await setupEditor("<p>\u200Bt[]ext</p>");
        const cursors = editor.shared.preserveSelection();
        cleanTextNode(el.querySelector("p").firstChild, "\u200B", cursors);
        cursors.restore();
        expect(getContent(el)).toBe("<p>t[]ext</p>");
    });
    test("should remove ZWS after cursor and preserve it", async () => {
        const { editor, el } = await setupEditor("<p>text[]\u200B</p>");
        const cursors = editor.shared.preserveSelection();
        cleanTextNode(el.querySelector("p").firstChild, "\u200B", cursors);
        cursors.restore();
        expect(getContent(el)).toBe("<p>text[]</p>");
    });
    test("should remove ZWS after cursor and preserve it (2)", async () => {
        const { editor, el } = await setupEditor("<p>t[]ext\u200B</p>");
        const cursors = editor.shared.preserveSelection();
        cleanTextNode(el.querySelector("p").firstChild, "\u200B", cursors);
        cursors.restore();
        expect(getContent(el)).toBe("<p>t[]ext</p>");
    });
    test("should remove multiple ZWS preserving cursor", async () => {
        const { editor, el } = await setupEditor("<p>\u200Bt\u200Be[]\u200Bxt\u200B</p>");
        const cursors = editor.shared.preserveSelection();
        cleanTextNode(el.querySelector("p").firstChild, "\u200B", cursors);
        cursors.restore();
        expect(getContent(el)).toBe("<p>te[]xt</p>");
    });
    test("should remove multiple ZWNBSP preserving cursor", async () => {
        const { editor, el } = await setupEditor("<p>\uFEFFt\uFEFFe[]\uFEFFxt\uFEFF</p>");
        const cursors = editor.shared.preserveSelection();
        cleanTextNode(el.querySelector("p").firstChild, "\uFEFF", cursors);
        cursors.restore();
        expect(getContent(el)).toBe("<p>te[]xt</p>");
    });
});
