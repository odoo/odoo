import { describe, expect, test } from "@odoo/hoot";
import { manuallyDispatchProgrammaticEvent, press, queryFirst } from "@odoo/hoot-dom";
import { setupEditor, testEditor } from "./_helpers/editor";
import { getContent, setSelection } from "./_helpers/selection";
import { insertText, tripleClick, undo } from "./_helpers/user_actions";
import { animationFrame, tick } from "@odoo/hoot-mock";

function setTag(tagName) {
    return (editor) => editor.shared.dom.setTag({ tagName });
}

describe("to paragraph", () => {
    test("should turn a heading 1 into a paragraph", async () => {
        await testEditor({
            contentBefore: "<h1>ab[]cd</h1>",
            stepFunction: setTag("p"),
            contentAfter: "<p>ab[]cd</p>",
        });
    });

    test("should turn a heading 1 into a paragraph (character selected)", async () => {
        await testEditor({
            contentBefore: "<h1>a[b]c</h1>",
            stepFunction: setTag("p"),
            contentAfter: "<p>a[b]c</p>",
        });
    });

    test("should turn a heading 1, a paragraph and a heading 2 into three paragraphs", async () => {
        await testEditor({
            contentBefore: "<h1>a[b</h1><p>cd</p><h2>e]f</h2>",
            stepFunction: setTag("p"),
            contentAfter: "<p>a[b</p><p>cd</p><p>e]f</p>",
        });
    });

    test.skip("should turn a heading 1 into a paragraph after a triple click", async () => {
        await testEditor({
            contentBefore: "<h1>[ab</h1><h2>]cd</h2>",
            stepFunction: setTag("p"),
            contentAfter: "<p>[ab</p><h2>]cd</h2>",
        });
    });

    test("should turn a div into a paragraph (if div is eligible for a baseContainer)", async () => {
        await testEditor({
            contentBefore: `<div>[ab]</div>`,
            stepFunction: setTag("p"),
            contentAfter: "<p>[ab]</p>",
        });
    });

    test("should not turn an unbreakable div into a paragraph", async () => {
        await testEditor({
            contentBefore: `<div class="oe_unbreakable">[ab]</div>`,
            stepFunction: setTag("p"),
            contentAfter: `<div class="oe_unbreakable"><p>[ab]</p></div>`,
        });
    });

    test("should add paragraph tag when selection is changed to normal in list", async () => {
        await testEditor({
            contentBefore: "<ul><li><h1>[abcd]</h1></li></ul>",
            stepFunction: setTag("p"),
            contentAfter: `<ul><li><p>[abcd]</p></li></ul>`,
        });
    });

    test("should add paragraph tag when selection is changed to normal in list (2)", async () => {
        await testEditor({
            contentBefore: "<ul><li><h1>[ab<span>cd]</span></h1></li></ul>",
            stepFunction: setTag("p"),
            contentAfter: `<ul><li><p>[ab<span>cd]</span></p></li></ul>`,
        });
    });

    test("should add paragraph tag when selection is changed to normal in list (3)", async () => {
        await testEditor({
            contentBefore: "<ul><li><h1>[ab<span>cd]</span></h1><h2>ef</h2></li></ul>",
            stepFunction: setTag("p"),
            contentAfter: `<ul><li><p>[ab<span>cd]</span></p><h2>ef</h2></li></ul>`,
        });
    });

    test("should not add paragraph tag to normal text in list", async () => {
        await testEditor({
            contentBefore: "<ul><li>[abcd]</li></ul>",
            stepFunction: setTag("p"),
            contentAfter: `<ul><li>[abcd]</li></ul>`,
        });
    });

    test("should turn three table cells with heading 1 to table cells with paragraph", async () => {
        await testEditor({
            contentBefore:
                "<table><tbody><tr><td><h1>[a</h1></td><td><h1>b</h1></td><td><h1>c]</h1></td></tr></tbody></table>",
            stepFunction: setTag("p"),
            // The custom table selection is removed in cleanForSave and the selection is collapsed.
            contentAfter:
                "<table><tbody><tr><td><p>[a</p></td><td><p>b</p></td><td><p>c]</p></td></tr></tbody></table>",
        });
    });

    test("should not set the tag of non-editable elements", async () => {
        await testEditor({
            contentBefore:
                '<h1>[before</h1><h1 contenteditable="false">noneditable</h1><h1>after]</h1>',
            stepFunction: setTag("p"),
            contentAfter: '<p>[before</p><h1 contenteditable="false">noneditable</h1><p>after]</p>',
        });
    });

    test("apply 'Text' command", async () => {
        const { el, editor } = await setupEditor("<h1>ab[]cd</h1>");
        await insertText(editor, "/text");
        await animationFrame();
        expect(".active .o-we-command-name").toHaveText("Text");

        await press("enter");
        expect(getContent(el)).toBe("<p>ab[]cd</p>");
    });
});

describe("to heading 1", () => {
    test("should turn a paragraph into a heading 1", async () => {
        await testEditor({
            contentBefore: "<p>ab[]cd</p>",
            stepFunction: setTag("h1"),
            contentAfter: "<h1>ab[]cd</h1>",
        });
    });

    test("should turn a paragraph into a heading 1 (character selected)", async () => {
        await testEditor({
            contentBefore: "<p>a[b]c</p>",
            stepFunction: setTag("h1"),
            contentAfter: "<h1>a[b]c</h1>",
        });
    });

    test("should just turn the paragraph with selected content into a heading 1", async () => {
        await testEditor({
            contentBefore: "<p>[ab</p><p>]cd</p>",
            stepFunction: setTag("h1"),
            contentAfter: "<h1>[ab</h1><p>]cd</p>",
        });
    });

    test("should just turn the paragraph with selected content into a heading 1 (2)", async () => {
        await testEditor({
            contentBefore: "<p>ab[</p><p>cd]</p>",
            stepFunction: setTag("h1"),
            contentAfter: "<p>ab[</p><h1>cd]</h1>",
        });
    });

    test("should turn a paragraph, a heading 1 and a heading 2 into three headings 1", async () => {
        await testEditor({
            contentBefore: "<p>a[b</p><h1>cd</h1><h2>e]f</h2>",
            stepFunction: setTag("h1"),
            contentAfter: "<h1>a[b</h1><h1>cd</h1><h1>e]f</h1>",
        });
    });

    test.skip("should turn a paragraph into a heading 1 after a triple click", async () => {
        await testEditor({
            contentBefore: "<p>[ab</p><h2>]cd</h2>",
            stepFunction: setTag("h1"),
            contentAfter: "<h1>[ab</h1><h2>]cd</h2>",
        });
    });

    test("should turn a div into a heading 1 (if div is eligible for a baseContainer)", async () => {
        await testEditor({
            contentBefore: "<div>[ab]</div>",
            stepFunction: setTag("h1"),
            contentAfter: "<h1>[ab]</h1>",
        });
    });

    test("should turn three table cells with paragraph to table cells with heading 1", async () => {
        await testEditor({
            contentBefore:
                "<table><tbody><tr><td><p>[a</p></td><td><p>b</p></td><td><p>c]</p></td></tr></tbody></table>",
            stepFunction: setTag("h1"),
            // The custom table selection is removed in cleanForSave and the selection is collapsed.
            contentAfter:
                "<table><tbody><tr><td><h1>[a</h1></td><td><h1>b</h1></td><td><h1>c]</h1></td></tr></tbody></table>",
        });
    });

    test("should not transfer attributes of list to heading 1", async () => {
        await testEditor({
            contentBefore: '<ul><li class="nav-item">[abcd]</li></ul>',
            stepFunction: setTag("h1"),
            contentAfter: '<ul><li class="nav-item"><h1>[abcd]</h1></li></ul>',
        });
    });
});

describe("to heading 2", () => {
    test("should turn a heading 1 into a heading 2", async () => {
        await testEditor({
            contentBefore: "<h1>ab[]cd</h1>",
            stepFunction: setTag("h2"),
            contentAfter: "<h2>ab[]cd</h2>",
        });
    });

    test("should turn a heading 1 into a heading 2 (character selected)", async () => {
        await testEditor({
            contentBefore: "<h1>a[b]c</h1>",
            stepFunction: setTag("h2"),
            contentAfter: "<h2>a[b]c</h2>",
        });
    });

    test("should turn a heading 1, a heading 2 and a paragraph into three headings 2", async () => {
        await testEditor({
            contentBefore: "<h1>a[b</h1><h2>cd</h2><p>e]f</p>",
            stepFunction: setTag("h2"),
            contentAfter: "<h2>a[b</h2><h2>cd</h2><h2>e]f</h2>",
        });
    });

    test.skip("should turn a paragraph into a heading 2 after a triple click", async () => {
        await testEditor({
            contentBefore: "<p>[ab</p><h1>]cd</h1>",
            stepFunction: setTag("h2"),
            contentAfter: "<h2>[ab</h2><h1>]cd</h1>",
        });
    });

    test("should turn a div into a heading 2 (if div is eligible for a baseContainer)", async () => {
        await testEditor({
            contentBefore: "<div>[ab]</div>",
            stepFunction: setTag("h2"),
            contentAfter: "<h2>[ab]</h2>",
        });
    });

    test("should turn three table cells with paragraph to table cells with heading 2", async () => {
        await testEditor({
            contentBefore:
                "<table><tbody><tr><td><p>[a</p></td><td><p>b</p></td><td><p>c]</p></td></tr></tbody></table>",
            stepFunction: setTag("h2"),
            // The custom table selection is removed in cleanForSave and the selection is collapsed.
            contentAfter:
                "<table><tbody><tr><td><h2>[a</h2></td><td><h2>b</h2></td><td><h2>c]</h2></td></tr></tbody></table>",
        });
    });

    test("should not transfer attributes of list to heading 2", async () => {
        await testEditor({
            contentBefore: '<ul><li class="nav-item">[abcd]</li></ul>',
            stepFunction: setTag("h2"),
            contentAfter: '<ul><li class="nav-item"><h2>[abcd]</h2></li></ul>',
        });
    });
});

describe("to heading 3", () => {
    test("should turn a heading 1 into a heading 3", async () => {
        await testEditor({
            contentBefore: "<h1>ab[]cd</h1>",
            stepFunction: setTag("h3"),
            contentAfter: "<h3>ab[]cd</h3>",
        });
    });

    test("should turn a heading 1 into a heading 3 (character selected)", async () => {
        await testEditor({
            contentBefore: "<h1>a[b]c</h1>",
            stepFunction: setTag("h3"),
            contentAfter: "<h3>a[b]c</h3>",
        });
    });

    test("should turn a heading 1, a paragraph and a heading 2 into three headings 3", async () => {
        await testEditor({
            contentBefore: "<h1>a[b</h1><p>cd</p><h2>e]f</h2>",
            stepFunction: setTag("h3"),
            contentAfter: "<h3>a[b</h3><h3>cd</h3><h3>e]f</h3>",
        });
    });

    test.skip("should turn a paragraph into a heading 3 after a triple click", async () => {
        await testEditor({
            contentBefore: "<p>[ab</p><h1>]cd</h1>",
            stepFunction: setTag("h3"),
            contentAfter: "<h3>[ab</h3><h1>]cd</h1>",
        });
    });

    test("should turn a div into a heading 3 (if div is eligible for a baseContainer)", async () => {
        await testEditor({
            contentBefore: "<div>[ab]</div>",
            stepFunction: setTag("h3"),
            contentAfter: "<h3>[ab]</h3>",
        });
    });

    test("should turn three table cells with paragraph to table cells with heading 3", async () => {
        await testEditor({
            contentBefore:
                "<table><tbody><tr><td><p>[a</p></td><td><p>b</p></td><td><p>c]</p></td></tr></tbody></table>",
            stepFunction: setTag("h3"),
            // The custom table selection is removed in cleanForSave and the selection is collapsed.
            contentAfter:
                "<table><tbody><tr><td><h3>[a</h3></td><td><h3>b</h3></td><td><h3>c]</h3></td></tr></tbody></table>",
        });
    });

    test("should not transfer attributes of list to heading 3", async () => {
        await testEditor({
            contentBefore: '<ul><li class="nav-item">[abcd]</li></ul>',
            stepFunction: setTag("h3"),
            contentAfter: '<ul><li class="nav-item"><h3>[abcd]</h3></li></ul>',
        });
    });
});

describe("to pre", () => {
    test("should turn a heading 1 into a pre", async () => {
        await testEditor({
            contentBefore: "<h1>ab[]cd</h1>",
            stepFunction: setTag("pre"),
            contentAfter: "<pre>ab[]cd</pre>",
        });
    });

    test("should turn a heading 1 into a pre (character selected)", async () => {
        await testEditor({
            contentBefore: "<h1>a[b]c</h1>",
            stepFunction: setTag("pre"),
            contentAfter: "<pre>a[b]c</pre>",
        });
    });

    test("should turn a heading 1 a pre and a paragraph into three pres", async () => {
        await testEditor({
            contentBefore: "<h1>a[b</h1><pre>cd</pre><p>e]f</p>",
            stepFunction: setTag("pre"),
            contentAfter: "<pre>a[b</pre><pre>cd</pre><pre>e]f</pre>",
        });
    });

    test("should turn three table cells with paragraph to table cells with pre", async () => {
        await testEditor({
            contentBefore:
                "<table><tbody><tr><td><p>[a</p></td><td><p>b</p></td><td><p>c]</p></td></tr></tbody></table>",
            stepFunction: setTag("pre"),
            // The custom table selection is removed in cleanForSave and the selection is collapsed.
            contentAfter:
                "<table><tbody><tr><td><pre>[a</pre></td><td><pre>b</pre></td><td><pre>c]</pre></td></tr></tbody></table>",
        });
    });

    test("should turn a paragraph into pre preserving the cursor position", async () => {
        await testEditor({
            contentBefore: "<p>abcd<br>[]<br></p>",
            stepFunction: setTag("pre"),
            contentAfter: "<pre>abcd<br>[]<br></pre>",
        });
    });

    test("should not transfer attributes of list to pre", async () => {
        await testEditor({
            contentBefore: '<ul><li class="nav-item" id="test">[abcd]</li></ul>',
            stepFunction: setTag("pre"),
            contentAfter: '<ul><li class="nav-item" id="test"><pre>[abcd]</pre></li></ul>',
        });
    });

    test("apply 'Code' command", async () => {
        const { el, editor } = await setupEditor("<p>ab[]cd</p>");
        await insertText(editor, "/code");
        await animationFrame();
        expect(".active .o-we-command-name").toHaveText("Code");

        await press("enter");
        expect(getContent(el)).toBe("<pre>ab[]cd</pre>");
    });
});

describe("to blockquote", () => {
    test("should turn a blockquote into a paragraph", async () => {
        await testEditor({
            contentBefore: "<h1>ab[]cd</h1>",
            stepFunction: setTag("blockquote"),
            contentAfter: "<blockquote>ab[]cd</blockquote>",
        });
    });

    test("should turn a heading 1 into a blockquote (character selected)", async () => {
        await testEditor({
            contentBefore: "<h1>a[b]c</h1>",
            stepFunction: setTag("blockquote"),
            contentAfter: "<blockquote>a[b]c</blockquote>",
        });
    });

    test("should turn a heading 1, a paragraph and a heading 2 into three blockquote", async () => {
        await testEditor({
            contentBefore: "<h1>a[b</h1><p>cd</p><h2>e]f</h2>",
            stepFunction: setTag("blockquote"),
            contentAfter:
                "<blockquote>a[b</blockquote><blockquote>cd</blockquote><blockquote>e]f</blockquote>",
        });
    });

    test.skip("should turn a heading 1 into a blockquote after a triple click", async () => {
        await testEditor({
            contentBefore: "<h1>[ab</h1><h2>]cd</h2>",
            stepFunction: setTag("blockquote"),
            contentAfter: "<blockquote>[ab</blockquote><h2>]cd</h2>",
        });
    });

    test("should turn a div into a blockquote (if div is eligible for a baseContainer)", async () => {
        await testEditor({
            contentBefore: "<div>[ab]</div>",
            stepFunction: setTag("blockquote"),
            contentAfter: "<blockquote>[ab]</blockquote>",
        });
    });

    test("should turn three table cells with paragraph to table cells with blockquote", async () => {
        await testEditor({
            contentBefore:
                "<table><tbody><tr><td><p>[a</p></td><td><p>b</p></td><td><p>c]</p></td></tr></tbody></table>",
            stepFunction: setTag("blockquote"),
            // The custom table selection is removed in cleanForSave and the selection is collapsed.
            contentAfter:
                "<table><tbody><tr><td><blockquote>[a</blockquote></td><td><blockquote>b</blockquote></td><td><blockquote>c]</blockquote></td></tr></tbody></table>",
        });
    });

    test("should not transfer attributes of list to blockquote", async () => {
        await testEditor({
            contentBefore: '<ul><li class="nav-item" style="color: red;">[abcd]</li></ul>',
            stepFunction: setTag("blockquote"),
            contentAfter:
                '<ul><li class="nav-item" style="color: red;"><blockquote>[abcd]</blockquote></li></ul>',
        });
    });

    test("setTag should work when we remove the selection", async () => {
        const { editor, el } = await setupEditor("<p>ab[]cd</p>");
        editor.document.getSelection().removeAllRanges();
        expect(getContent(el)).toBe("<p>abcd</p>");

        setTag("h1")(editor);
        expect(getContent(el)).toBe("<h1>abcd</h1>");
    });

    test("setTag should work when we move the selection outside of the editor", async () => {
        const { editor, el } = await setupEditor("<p>ab[]cd</p>");
        const anchorNode = queryFirst(".odoo-editor-editable").parentElement;
        setSelection({ anchorNode, anchorOffset: 0 });
        expect(getContent(el)).toBe("<p>abcd</p>");

        setTag("h1")(editor);
        expect(getContent(el)).toBe("<h1>abcd</h1>");
    });

    test("triple click with setTag should only switch the tag on the selected line", async () => {
        const { editor, el } = await setupEditor("<p>ab[]cd</p><p>Plop</p>");
        // Simulate selection trigger by triple click
        // @todo @phoenix need to adapt when hoot add detail => 3 x click
        await tripleClick(queryFirst("div p"));
        expect(getContent(el)).toBe("<p>[abcd]</p><p>Plop</p>");

        setTag("h1")(editor);
        expect(getContent(el)).toBe("<h1>[abcd]</h1><p>Plop</p>");
    });

    test("6 click with setTag should only switch the tag on the selected line", async () => {
        const { editor, el } = await setupEditor("<p>ab[]cd</p><p>Plop</p>");
        // Simulate selection trigger by triple click
        // @todo @phoenix need to adapt when hoot add detail => 6 x click
        const anchorNode = queryFirst("div p");
        await manuallyDispatchProgrammaticEvent(anchorNode, "mousedown", { detail: 6 });
        setSelection({
            anchorNode,
            anchorOffset: 0,
            focusNode: anchorNode.nextSibling,
            focusOffset: 0,
        });
        await tick();
        expect(getContent(el)).toBe("<p>[abcd]</p><p>Plop</p>");

        setTag("h1")(editor);
        expect(getContent(el)).toBe("<h1>[abcd]</h1><p>Plop</p>");
    });

    test("apply 'Quote' command", async () => {
        const { el, editor } = await setupEditor("<p>ab[]cd</p>");
        await insertText(editor, "/quote");
        await animationFrame();
        expect(".active .o-we-command-name").toHaveText("Quote");

        await press("enter");
        expect(getContent(el)).toBe("<blockquote>ab[]cd</blockquote>");
    });

    test("setTag should work after control+a", async () => {
        const { el, editor } = await setupEditor("<p>[]abcd</p>");
        await press(["ctrl", "a"]);
        expect(getContent(el)).toBe("[<p>abcd</p>]");
        setTag("h1")(editor);
        expect(getContent(el)).toBe("[<h1>abcd</h1>]");
    });
});

describe("transform", () => {
    test("should transform space preceding by a hashtag to heading 1", async () => {
        const { el, editor } = await setupEditor("<p>[]</p>");
        await insertText(editor, "# ");
        expect(getContent(el)).toBe(`<h1 placeholder="Heading 1" class="o-we-hint">[]<br></h1>`);

        undo(editor);
        expect(getContent(el)).toBe(`<p># []</p>`);
    });

    test("should transform space preceding by two hashtags to heading 2", async () => {
        const { el, editor } = await setupEditor("<p>[]</p>");
        await insertText(editor, "## ");
        expect(getContent(el)).toBe(`<h2 placeholder="Heading 2" class="o-we-hint">[]<br></h2>`);
    });

    test("should transform space preceding by three hashtags to heading 3", async () => {
        const { el, editor } = await setupEditor("<p>[]<br></p>");
        await insertText(editor, "### ");
        expect(getContent(el)).toBe(`<h3 placeholder="Heading 3" class="o-we-hint">[]<br></h3>`);
    });

    test("should transform space preceding by a hashtag at the starting of text to heading 1", async () => {
        const { el, editor } = await setupEditor("<p>[]abc</p>");
        await insertText(editor, "# ");
        expect(getContent(el)).toBe(`<h1>[]abc</h1>`);

        undo(editor);
        expect(getContent(el)).toBe(`<p># []abc</p>`);
    });

    test("should transform space preceding by two hashtags at the starting of text to heading 2", async () => {
        const { el, editor } = await setupEditor("<p>[]abc</p>");
        await insertText(editor, "## ");
        expect(getContent(el)).toBe(`<h2>[]abc</h2>`);
    });

    test("should transform space preceding by three hashtags at the starting of text to heading 3", async () => {
        const { el, editor } = await setupEditor("<p>[]abc</p>");
        await insertText(editor, "### ");
        expect(getContent(el)).toBe(`<h3>[]abc</h3>`);
    });

    test("typing space inside formated text with a hashtag at the starting of text should not transform to heading", async () => {
        const { el, editor } = await setupEditor("<p># a<strong>b[]cd</strong>e</p>");
        await insertText(editor, " ");
        expect(getContent(el)).toBe(`<p># a<strong>b []cd</strong>e</p>`);
    });
});
