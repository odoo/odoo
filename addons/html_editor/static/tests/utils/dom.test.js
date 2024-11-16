import { describe, expect, test } from "@odoo/hoot";
import { setupEditor } from "../_helpers/editor";
import {
    cleanTextNode,
    fillEmpty,
    splitTextNode,
    wrapInlinesInBlocks,
} from "@html_editor/utils/dom";
import { getContent } from "../_helpers/selection";
import { parseHTML } from "@html_editor/utils/html";
import { unformat } from "../_helpers/format";

describe("splitAroundUntil", () => {
    test("should split a slice of text from its inline ancestry (1)", async () => {
        const { editor, el } = await setupEditor("<p>a<font>b<span>cde</span>f</font>g</p>");
        const [p] = el.childNodes;
        const cde = p.childNodes[1].childNodes[1].firstChild;
        // We want to test with "cde" being three separate text nodes.
        splitTextNode(cde, 2);
        const cd = cde.previousSibling;
        splitTextNode(cd, 1);
        const d = cd;
        const result = editor.shared.split.splitAroundUntil(d, p.childNodes[1]);
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
        splitTextNode(cdefg, 4);
        const cdef = cdefg.previousSibling;
        splitTextNode(cdef, 3);
        const cde = cdef.previousSibling;
        splitTextNode(cde, 2);
        const cd = cde.previousSibling;
        splitTextNode(cd, 1);
        const d = cd;
        const result = editor.shared.split.splitAroundUntil(
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
        const result = editor.shared.split.splitAroundUntil(cde, font);
        expect(result.tagName === "FONT" && result !== font).toBe(true);
        expect(p.outerHTML).toBe(
            "<p>a<font>b</font><font><span>cde</span></font><font>f</font>g</p>"
        );
    });

    test("should not do anything (nothing to split)", async () => {
        const { editor, el } = await setupEditor("<p>a<font><span>bcd</span></font>e</p>");
        const [p] = el.childNodes;
        const bcd = p.querySelector("span").firstChild;
        const result = editor.shared.split.splitAroundUntil(bcd, p.childNodes[1]);
        expect(result === p.childNodes[1]).toBe(true);
        expect(p.outerHTML).toBe("<p>a<font><span>bcd</span></font>e</p>");
    });
});

describe("cleanTextNode", () => {
    test("should remove ZWS before cursor and preserve it", async () => {
        const { editor, el } = await setupEditor("<p>\u200B[]text</p>");
        const cursors = editor.shared.selection.preserveSelection();
        cleanTextNode(el.querySelector("p").firstChild, "\u200B", cursors);
        cursors.restore();
        expect(getContent(el)).toBe("<p>[]text</p>");
    });
    test("should remove ZWS before cursor and preserve it (2)", async () => {
        const { editor, el } = await setupEditor("<p>\u200Bt[]ext</p>");
        const cursors = editor.shared.selection.preserveSelection();
        cleanTextNode(el.querySelector("p").firstChild, "\u200B", cursors);
        cursors.restore();
        expect(getContent(el)).toBe("<p>t[]ext</p>");
    });
    test("should remove ZWS after cursor and preserve it", async () => {
        const { editor, el } = await setupEditor("<p>text[]\u200B</p>");
        const cursors = editor.shared.selection.preserveSelection();
        cleanTextNode(el.querySelector("p").firstChild, "\u200B", cursors);
        cursors.restore();
        expect(getContent(el)).toBe("<p>text[]</p>");
    });
    test("should remove ZWS after cursor and preserve it (2)", async () => {
        const { editor, el } = await setupEditor("<p>t[]ext\u200B</p>");
        const cursors = editor.shared.selection.preserveSelection();
        cleanTextNode(el.querySelector("p").firstChild, "\u200B", cursors);
        cursors.restore();
        expect(getContent(el)).toBe("<p>t[]ext</p>");
    });
    test("should remove multiple ZWS preserving cursor", async () => {
        const { editor, el } = await setupEditor("<p>\u200Bt\u200Be[]\u200Bxt\u200B</p>");
        const cursors = editor.shared.selection.preserveSelection();
        cleanTextNode(el.querySelector("p").firstChild, "\u200B", cursors);
        cursors.restore();
        expect(getContent(el)).toBe("<p>te[]xt</p>");
    });
    test("should remove multiple ZWNBSP preserving cursor", async () => {
        const { editor, el } = await setupEditor("<p>\uFEFFt\uFEFFe[]\uFEFFxt\uFEFF</p>");
        const cursors = editor.shared.selection.preserveSelection();
        cleanTextNode(el.querySelector("p").firstChild, "\uFEFF", cursors);
        cursors.restore();
        expect(getContent(el)).toBe("<p>te[]xt</p>");
    });
});

describe("wrapInlinesInBlocks", () => {
    test("should wrap text node in P", async () => {
        const div = document.createElement("div");
        div.innerHTML = "text";
        wrapInlinesInBlocks(div);
        expect(div.innerHTML).toBe("<p>text</p>");
    });
    test("should wrap inline element in P", async () => {
        const div = document.createElement("div");
        div.innerHTML = "<strong>text</strong>";
        wrapInlinesInBlocks(div);
        expect(div.innerHTML).toBe("<p><strong>text</strong></p>");
    });
    test("should not do anything to block element", async () => {
        const div = document.createElement("div");
        div.innerHTML = "<p>text</p>";
        wrapInlinesInBlocks(div);
        expect(div.innerHTML).toBe("<p>text</p>");
    });
    test("should wrap inlines in P", async () => {
        const div = document.createElement("div");
        div.innerHTML = "textnode<strong>inline</strong><p>p</p>";
        wrapInlinesInBlocks(div);
        expect(div.innerHTML).toBe("<p>textnode<strong>inline</strong></p><p>p</p>");
    });
    test("should wrap inlines in P (2)", async () => {
        const div = document.createElement("div");
        div.innerHTML = "<strong>inline</strong><p>p</p>textnode";
        wrapInlinesInBlocks(div);
        expect(div.innerHTML).toBe("<p><strong>inline</strong></p><p>p</p><p>textnode</p>");
    });
    test("should turn a BR into a paragraph break", async () => {
        const div = document.createElement("div");
        div.innerHTML = "abc<br>def";
        wrapInlinesInBlocks(div);
        expect(div.innerHTML).toBe("<p>abc</p><p>def</p>");
    });
    test("should remove a BR that has no effect", async () => {
        const div = document.createElement("div");
        div.innerHTML = "abc<br>def<br>";
        wrapInlinesInBlocks(div);
        expect(div.innerHTML).toBe("<p>abc</p><p>def</p>");
    });
    test("empty lines should become empty paragraphs", async () => {
        const div = document.createElement("div");
        div.innerHTML = "abc<br><br>def";
        wrapInlinesInBlocks(div);
        expect(div.innerHTML).toBe("<p>abc</p><p><br></p><p>def</p>");
    });
    test("empty lines should become empty paragraphs (2)", async () => {
        const div = document.createElement("div");
        div.innerHTML = "<br>";
        wrapInlinesInBlocks(div);
        expect(div.innerHTML).toBe("<p><br></p>");
    });
    test("empty lines should become empty paragraphs (3)", async () => {
        const div = document.createElement("div");
        div.innerHTML = "<br>abc";
        wrapInlinesInBlocks(div);
        expect(div.innerHTML).toBe("<p><br></p><p>abc</p>");
    });
    test("mix: handle blocks, inlines and BRs", async () => {
        const div = document.createElement("div");
        div.innerHTML = "a<br><strong>b</strong><h1>c</h1><br>d<h2>e</h2><br>";
        wrapInlinesInBlocks(div);
        expect(div.innerHTML).toBe(
            "<p>a</p><p><strong>b</strong></p><h1>c</h1><p><br></p><p>d</p><h2>e</h2><p><br></p>"
        );
    });
    test("wrap block with display style inline in div", async () => {
        // Second part should be wrapped automatically during initElementForEdition
        const { el, editor } = await setupEditor(
            `<div><br></div><div contenteditable="false" style="display: inline;">inline</div>`
        );
        const div = el.querySelector("div");
        editor.shared.selection.setSelection({ anchorNode: div, anchorOffset: 0 });
        editor.shared.selection.focusEditable();
        editor.shared.dom.insert(
            parseHTML(
                editor.document,
                `<div contenteditable="false" style="display: inline;">inline</div>`
            )
        );
        // First part (inserted content) is wrapped manually
        wrapInlinesInBlocks(div);
        expect(getContent(el)).toBe(
            unformat(`
                    <div>
                        <div>
                            <div contenteditable="false" style="display: inline;">inline</div>
                        </div>[]
                    </div>
                    <div style="margin-bottom: 0px;">
                        <div contenteditable="false" style="display: inline;">inline</div>
                    </div>
            `)
        );
    });
    test("wrap a mix of inline elements in div", async () => {
        // Second part should be wrapped automatically during initElementForEdition
        const { el, editor } = await setupEditor(
            `<div><br></div>text<div contenteditable="false" style="display: inline;">inline</div><span class="a">span</span>`
        );
        const div = el.querySelector("div");
        editor.shared.selection.setSelection({ anchorNode: div, anchorOffset: 0 });
        editor.shared.selection.focusEditable();
        editor.shared.dom.insert(
            parseHTML(
                editor.document,
                `text<div contenteditable="false" style="display: inline;">inline</div><span class="a">span</span>`
            )
        );
        // First part (inserted content) is wrapped manually
        wrapInlinesInBlocks(div);
        expect(getContent(el)).toBe(
            unformat(`
                <div>
                    <div>
                        text<div contenteditable="false" style="display: inline;">inline</div><span class="a">span</span>
                    </div>[]
                </div>
                <div style="margin-bottom: 0px;">
                    text<div contenteditable="false" style="display: inline;">inline</div><span class="a">span</span>
                </div>
            `)
        );
    });
    test("wrap a mix of inline elements in div with br", async () => {
        // Second part should be wrapped automatically during initElementForEdition
        const { el, editor } = await setupEditor(
            `<div>[]<br></div>text<br><div contenteditable="false" style="display: inline;">inline</div><br><span class="a">span</span>`
        );
        const div = el.querySelector("div");
        editor.shared.selection.setSelection({ anchorNode: div, anchorOffset: 0 });
        editor.shared.dom.insert(
            parseHTML(
                editor.document,
                `text<br><div contenteditable="false" style="display: inline;">inline</div><br><span class="a">span</span>`
            )
        );
        // First part (inserted content) is wrapped manually
        wrapInlinesInBlocks(div);
        expect(getContent(el)).toBe(
            unformat(`
                <div>
                    <p>text</p>
                    <div>
                        <div contenteditable="false" style="display: inline;">inline</div>
                    </div>
                    <p><span class="a">span</span></p>[]
                </div>
                <p style="margin-bottom: 0px;">text</p>
                <div style="margin-bottom: 0px;">
                    <div contenteditable="false" style="display: inline;">inline</div>
                </div>
                <p style="margin-bottom: 0px;"><span class="a">span</span></p>
            `)
        );
    });
});

describe("fillEmpty", () => {
    test("should not add fill a shrunk protected block, nor add a ZWS to it", async () => {
        const { el } = await setupEditor('<div data-oe-protected="true"></div>');
        expect(el.innerHTML).toBe('<div data-oe-protected="true" contenteditable="false"></div>');
        const div = el.firstChild;
        fillEmpty(div);
        expect(el.innerHTML).toBe('<div data-oe-protected="true" contenteditable="false"></div>');
    });
});
