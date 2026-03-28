import { describe, expect, test } from "@odoo/hoot";
import { deleteBackward, insertText } from "../_helpers/user_actions";
import { setupEditor, testEditor } from "../_helpers/editor";
import { descendants } from "@html_editor/utils/dom_traversal";
import { tick } from "@odoo/hoot-mock";
import { getContent, setSelection } from "../_helpers/selection";
import { cleanLinkArtifacts } from "../_helpers/format";
import { animationFrame, pointerDown, pointerUp, queryOne } from "@odoo/hoot-dom";
import { dispatchNormalize } from "../_helpers/dispatch";
import { nodeSize } from "@html_editor/utils/position";
import { expectElementCount } from "../_helpers/ui_expectations";

test("should pad a link with ZWNBSPs and add visual indication", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="http://test.test/">b</a>c</p>',
        contentBeforeEdit: '<p>a\ufeff<a href="http://test.test/">\ufeffb\ufeff</a>\ufeffc</p>',
        stepFunction: async (editor) => {
            setSelection({ anchorNode: editor.editable.querySelector("a"), anchorOffset: 1 });
            await tick();
        },
        contentAfterEdit:
            '<p>a\ufeff<a href="http://test.test/" class="o_link_in_selection">\ufeff[]b\ufeff</a>\ufeffc</p>',
        contentAfter: '<p>a<a href="http://test.test/">[]b</a>c</p>',
    });
});

test("should pad a link with ZWNBSPs and add visual indication (2)", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="http://test.test/"><span class="a">b</span></a></p>',
        contentBeforeEdit:
            '<p>a\ufeff<a href="http://test.test/">\ufeff<span class="a">b</span>\ufeff</a>\ufeff</p>',
        stepFunction: async (editor) => {
            setSelection({ anchorNode: editor.editable.querySelector("a span"), anchorOffset: 0 });
            await tick();
        },
        contentAfterEdit:
            '<p>a\ufeff<a href="http://test.test/" class="o_link_in_selection">\ufeff<span class="a">[]b</span>\ufeff</a>\ufeff</p>',
        contentAfter: '<p>a<a href="http://test.test/"><span class="a">[]b</span></a></p>',
    });
});

test("should keep link padded with ZWNBSPs after a delete", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="http://test.test/">b[]</a>c</p>',
        stepFunction: deleteBackward,
        contentAfterEdit:
            '<p>a\ufeff<a href="http://test.test/" class="o_link_in_selection">\ufeff[]\ufeff</a>\ufeffc</p>',
        contentAfter: "<p>a[]c</p>",
    });
});

test("should keep isolated link after a delete and typing", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="http://test.test/">b[]</a>c</p>',
        stepFunction: async (editor) => {
            deleteBackward(editor);
            await insertText(editor, "a");
            await insertText(editor, "b");
            await insertText(editor, "c");
        },
        contentAfter: '<p>a<a href="http://test.test/">abc[]</a>c</p>',
    });
});

test("should delete the content from the link when popover is active", async () => {
    const { editor, el } = await setupEditor('<p><a href="http://test.test/">abc[]abc</a></p>');
    await expectElementCount(".o-we-linkpopover", 1);
    deleteBackward(editor);
    deleteBackward(editor);
    deleteBackward(editor);
    const content = getContent(el);
    expect(content).toBe(
        '<p>\ufeff<a href="http://test.test/" class="o_link_in_selection">\ufeff[]abc\ufeff</a>\ufeff</p>'
    );
    expect(cleanLinkArtifacts(content)).toBe('<p><a href="http://test.test/">[]abc</a></p>');
});

describe.tags("desktop");
describe("should position the cursor outside the link", () => {
    test("clicking at the start of the link", async () => {
        const { el } = await setupEditor('<p><a href="http://test.test/">te[]st</a></p>');
        expect(getContent(el)).toBe(
            '<p>\ufeff<a href="http://test.test/" class="o_link_in_selection">\ufeffte[]st\ufeff</a>\ufeff</p>'
        );

        const aElement = queryOne("p a");
        await pointerDown(el);
        // Simulate the selection with mousedown
        setSelection({ anchorNode: aElement.childNodes[0], anchorOffset: 0 });
        expect(getContent(el)).toBe(
            '<p>\ufeff<a href="http://test.test/" class="o_link_in_selection">[]\ufefftest\ufeff</a>\ufeff</p>'
        );
        await animationFrame(); // selection change
        await pointerUp(el);
        expect(getContent(el)).toBe(
            '<p>[]\ufeff<a href="http://test.test/">\ufefftest\ufeff</a>\ufeff</p>'
        );
    });

    test("clicking at the start of the link when format is applied on link", async () => {
        const { el } = await setupEditor('<p><strong><a href="#/">test</a></strong></p>');
        expect(getContent(el)).toBe(
            // The editable selection is in the link (first leaf of the editable
            // upon initialization).
            '<p><strong>\ufeff<a href="#/">\ufefftest\ufeff</a>\ufeff</strong></p>'
        );

        const aElement = queryOne("p a");
        await pointerDown(el);
        // Simulate the selection with mousedown
        setSelection({ anchorNode: aElement.childNodes[0], anchorOffset: 0 });
        expect(getContent(el)).toBe(
            '<p><strong>\ufeff<a href="#/">[]\ufefftest\ufeff</a>\ufeff</strong></p>'
        );
        await animationFrame(); // selection change
        await pointerUp(el);
        expect(getContent(el)).toBe(
            '<p><strong>[]\ufeff<a href="#/">\ufefftest\ufeff</a>\ufeff</strong></p>'
        );
    });

    test("clicking at the end of the link", async () => {
        const { el } = await setupEditor('<p><a href="http://test.test/">te[]st</a></p>');
        expect(getContent(el)).toBe(
            '<p>\ufeff<a href="http://test.test/" class="o_link_in_selection">\ufeffte[]st\ufeff</a>\ufeff</p>'
        );

        const aElement = queryOne("p a");
        await pointerDown(el);
        // Simulate the selection with mousedown
        setSelection({
            anchorNode: aElement.childNodes[2],
            anchorOffset: nodeSize(aElement.childNodes[2]),
        });
        expect(getContent(el)).toBe(
            '<p>\ufeff<a href="http://test.test/" class="o_link_in_selection">\ufefftest\ufeff[]</a>\ufeff</p>'
        );
        await animationFrame(); // selectionChange
        await pointerUp(el);
        expect(getContent(el)).toBe(
            '<p>\ufeff<a href="http://test.test/">\ufefftest\ufeff</a>\ufeff[]</p>'
        );
    });

    test("clicking before the link's text content", async () => {
        const { el, editor } = await setupEditor('<p><a href="http://test.test/">te[]st</a></p>');
        expect(getContent(el)).toBe(
            '<p>\ufeff<a href="http://test.test/" class="o_link_in_selection">\ufeffte[]st\ufeff</a>\ufeff</p>'
        );

        const aElement = queryOne("p a");
        await pointerDown(el);
        // Simulate the selection with mousedown
        setSelection({ anchorNode: aElement.childNodes[1], anchorOffset: 0 });
        expect(getContent(el)).toBe(
            '<p>\ufeff<a href="http://test.test/" class="o_link_in_selection">\ufeff[]test\ufeff</a>\ufeff</p>'
        );
        await animationFrame(); // selection change
        await pointerUp(el);
        expect(getContent(el)).toBe(
            '<p>[]\ufeff<a href="http://test.test/">\ufefftest\ufeff</a>\ufeff</p>'
        );

        await insertText(editor, "link");
        expect(getContent(el)).toBe(
            '<p>link[]\ufeff<a href="http://test.test/">\ufefftest\ufeff</a>\ufeff</p>'
        );

        setSelection({ anchorNode: aElement.childNodes[1], anchorOffset: 0 });
        await animationFrame(); // selectionChange
        expect(getContent(el)).toBe(
            '<p>link\ufeff<a href="http://test.test/" class="o_link_in_selection">\ufeff[]test\ufeff</a>\ufeff</p>'
        );
        await insertText(editor, "content");
        expect(getContent(el)).toBe(
            '<p>link\ufeff<a href="http://test.test/" class="o_link_in_selection">\ufeffcontent[]test\ufeff</a>\ufeff</p>'
        );
    });

    test(" clicking after the link's text content", async () => {
        const { el, editor } = await setupEditor('<p><a href="http://test.test/">t[]est</a></p>');
        expect(getContent(el)).toBe(
            '<p>\ufeff<a href="http://test.test/" class="o_link_in_selection">\ufefft[]est\ufeff</a>\ufeff</p>'
        );

        const aElement = queryOne("p a");
        await pointerDown(el);
        // Simulate the selection with mousedown
        setSelection({
            anchorNode: aElement.childNodes[1],
            anchorOffset: nodeSize(aElement.childNodes[1]),
        });
        expect(getContent(el)).toBe(
            '<p>\ufeff<a href="http://test.test/" class="o_link_in_selection">\ufefftest[]\ufeff</a>\ufeff</p>'
        );
        await animationFrame(); // selection change
        await pointerUp(el);
        expect(getContent(el)).toBe(
            '<p>\ufeff<a href="http://test.test/">\ufefftest\ufeff</a>\ufeff[]</p>'
        );

        await insertText(editor, "link");
        expect(getContent(el)).toBe(
            '<p>\ufeff<a href="http://test.test/">\ufefftest\ufeff</a>\ufefflink[]</p>'
        );

        setSelection({
            anchorNode: aElement.childNodes[1],
            anchorOffset: nodeSize(aElement.childNodes[1]),
        });
        await animationFrame(); // selectionChange
        expect(getContent(el)).toBe(
            '<p>\ufeff<a href="http://test.test/" class="o_link_in_selection">\ufefftest[]\ufeff</a>\ufefflink</p>'
        );
        await insertText(editor, "content");
        expect(getContent(el)).toBe(
            '<p>\ufeff<a href="http://test.test/" class="o_link_in_selection">\ufefftestcontent[]\ufeff</a>\ufefflink</p>'
        );
    });
});

describe("should zwnbsp-pad simple text link", () => {
    const removeZwnbsp = (editor) => {
        for (const descendant of descendants(editor.editable)) {
            if (descendant.nodeType === Node.TEXT_NODE && descendant.textContent === "\ufeff") {
                descendant.remove();
            }
        }
    };
    test("should zwnbsp-pad simple text link (1)", async () => {
        await testEditor({
            contentBefore: '<p>a[]<a href="#/">bc</a>d</p>',
            contentBeforeEdit: '<p>a[]\ufeff<a href="#/">\ufeffbc\ufeff</a>\ufeffd</p>',
            stepFunction: async (editor) => {
                removeZwnbsp(editor);
                const p = editor.editable.querySelector("p");
                // set the selection via the parent
                setSelection({ anchorNode: p, anchorOffset: 1 });
                // insert the zwnbsp again
                dispatchNormalize(editor);
            },
            contentAfterEdit: '<p>a\ufeff[]<a href="#/">\ufeffbc\ufeff</a>\ufeffd</p>',
        });
    });
    test("should zwnbsp-pad simple text link (2)", async () => {
        await testEditor({
            contentBefore: '<p>a<a href="http://test.test/">[]bc</a>d</p>',
            contentBeforeEdit:
                '<p>a\ufeff<a href="http://test.test/" class="o_link_in_selection">\ufeff[]bc\ufeff</a>\ufeffd</p>',
            stepFunction: async (editor) => {
                removeZwnbsp(editor);
                const a = editor.editable.querySelector("a");
                // set the selection via the parent
                setSelection({ anchorNode: a, anchorOffset: 0 });
                await tick();
                // insert the zwnbsp again
                dispatchNormalize(editor);
            },
            contentAfterEdit:
                '<p>a\ufeff<a href="http://test.test/" class="o_link_in_selection">\ufeff[]bc\ufeff</a>\ufeffd</p>',
        });
    });
    test("should zwnbsp-pad simple text link (3)", async () => {
        await testEditor({
            contentBefore: '<p>a<a href="http://test.test/">b[]</a>d</p>',
            contentBeforeEdit:
                '<p>a\ufeff<a href="http://test.test/" class="o_link_in_selection">\ufeffb[]\ufeff</a>\ufeffd</p>',
            stepFunction: async (editor) => {
                const a = editor.editable.querySelector("a");
                // Insert an extra character as a text node so we can set
                // the selection between the characters while still
                // targetting their parent.
                a.appendChild(editor.document.createTextNode("c"));
                removeZwnbsp(editor);
                // set the selection via the parent
                setSelection({ anchorNode: a, anchorOffset: 1 });
                await tick();
                // insert the zwnbsp again
                dispatchNormalize(editor);
            },
            contentAfterEdit:
                '<p>a\ufeff<a href="http://test.test/" class="o_link_in_selection">\ufeffb[]c\ufeff</a>\ufeffd</p>',
        });
    });
    test("should zwnbsp-pad simple text link (4)", async () => {
        await testEditor({
            contentBefore: '<p>a<a href="http://test.test/">bc[]</a>d</p>',
            contentBeforeEdit:
                '<p>a\ufeff<a href="http://test.test/" class="o_link_in_selection">\ufeffbc[]\ufeff</a>\ufeffd</p>',
            stepFunction: async (editor) => {
                removeZwnbsp(editor);
                const a = editor.editable.querySelector("a");
                // set the selection via the parent
                setSelection({ anchorNode: a, anchorOffset: 1 });
                await tick();
                // insert the zwnbsp again
                dispatchNormalize(editor);
            },
            contentAfterEdit:
                '<p>a\ufeff<a href="http://test.test/" class="o_link_in_selection">\ufeffbc[]\ufeff</a>\ufeffd</p>',
        });
    });
    test("should zwnbsp-pad simple text link (5)", async () => {
        await testEditor({
            contentBefore: '<p>a<a href="#/">bc</a>[]d</p>',
            contentBeforeEdit: '<p>a\ufeff<a href="#/">\ufeffbc\ufeff</a>\ufeff[]d</p>',
            stepFunction: async (editor) => {
                removeZwnbsp(editor);
                const p = editor.editable.querySelector("p");
                // set the selection via the parent
                setSelection({ anchorNode: p, anchorOffset: 2 });
                await tick();
                // insert the zwnbsp again
                dispatchNormalize(editor);
            },
            contentAfterEdit: '<p>a\ufeff<a href="#/">\ufeffbc\ufeff</a>\ufeff[]d</p>',
        });
    });
});

test("should not zwnbsp-pad nav-link", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="http://test.test/" class="nav-link">[]b</a>c</p>',
        contentBeforeEdit: '<p>a<a href="http://test.test/" class="nav-link">[]b</a>c</p>',
    });
});

test("should not zwnbsp-pad link with block fontawesome", async () => {
    await testEditor({
        contentBefore:
            '<p>a<a href="http://test.test/">[]<i style="display: flex;" class="fa fa-star"></i></a>b</p>',
        contentBeforeEdit:
            '<p>a<a href="http://test.test/">\ufeff[]<i style="display: flex;" class="fa fa-star" contenteditable="false">\u200b</i>\ufeff</a>b</p>',
    });
});

test("should not zwnbsp-pad link with image", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="http://test.test/">[]<img style="display: inline;"></a>b</p>',
        contentBeforeEdit:
            '<p>a<a href="http://test.test/">[]<img style="display: inline;"></a>b</p>',
    });
});

test("should remove zwnbsp from middle of the link", async () => {
    await testEditor({
        contentBefore: '<p><a href="#/">content</a></p>',
        contentBeforeEdit:
            // The editable selection is in the link (first leaf of the editable
            // upon initialization).
            '<p>\ufeff<a href="#/">\ufeffcontent\ufeff</a>\ufeff</p>',
        stepFunction: async (editor) => {
            // Cursor before the FEFF text node
            setSelection({ anchorNode: editor.editable.querySelector("a"), anchorOffset: 0 });
            await insertText(editor, "more ");
        },
        contentAfterEdit:
            '<p>\ufeff<a href="#/" class="o_link_in_selection">\ufeffmore []content\ufeff</a>\ufeff</p>',
        contentAfter: '<p><a href="#/">more []content</a></p>',
    });
});

test("should remove zwnbsp from middle of the link (2)", async () => {
    await testEditor({
        contentBefore: '<p><a href="#/">content</a></p>',
        contentBeforeEdit:
            // The editable selection is in the link (first leaf of the editable
            // upon initialization).
            '<p>\ufeff<a href="#/">\ufeffcontent\ufeff</a>\ufeff</p>',
        stepFunction: async (editor) => {
            // Cursor inside the FEFF text node
            setSelection({
                anchorNode: editor.editable.querySelector("a").firstChild,
                anchorOffset: 0,
            });
            await insertText(editor, "more ");
        },
        contentAfterEdit:
            '<p>\ufeff<a href="#/" class="o_link_in_selection">\ufeffmore []content\ufeff</a>\ufeff</p>',
        contentAfter: '<p><a href="#/">more []content</a></p>',
    });
});

describe("button", () => {
    test("should zwnbps-pad links with .btn class", async () => {
        await testEditor({
            contentBefore: '<p><a href="#" class="btn">content</a></p>',
            contentBeforeEdit: '<p>\ufeff<a href="#" class="btn">\ufeffcontent\ufeff</a>\ufeff</p>',
        });
    });

    test("should not add visual indication to a button", async () => {
        await testEditor({
            contentBefore: '<p><a href="http://test.test/" class="btn">[]content</a></p>',
            contentBeforeEdit:
                '<p>\ufeff<a href="http://test.test/" class="btn">\ufeff[]content\ufeff</a>\ufeff</p>',
        });
    });

    test("should type inside button after backspacing into it", async () => {
        const { editor, el } = await setupEditor(
            '<p>before<a class="btn" href="#/">in</a>x[]after</p>'
        );
        expect(getContent(el)).toBe(
            '<p>before\ufeff<a class="btn" href="#/">\ufeffin\ufeff</a>\ufeffx[]after</p>'
        );
        deleteBackward(editor);
        expect(getContent(el)).toBe(
            '<p>before\ufeff<a class="btn" href="#/">\ufeffin\ufeff</a>\ufeff[]after</p>'
        );
        deleteBackward(editor);
        expect(getContent(el)).toBe(
            '<p>before\ufeff<a class="btn" href="#/">\ufeffin[]\ufeff</a>\ufeffafter</p>'
        );
        await insertText(editor, "side");
        expect(getContent(el)).toBe(
            '<p>before\ufeff<a class="btn" href="#/">\ufeffinside[]\ufeff</a>\ufeffafter</p>'
        );
    });
});

test("Should not highlight link if editable not focused", async () => {
    const { el } = await setupEditor('<p><a href="http://test.test/">abc</a></p>');
    expect(getContent(el)).toBe(
        '<p>\ufeff<a href="http://test.test/">\ufeffabc\ufeff</a>\ufeff</p>'
    );
});

test("Should highlight link if editable focused", async () => {
    const { el } = await setupEditor('<p><a href="http://test.test/">abc</a></p>');
    el.focus();
    setSelection({ anchorNode: el.querySelector("a"), anchorOffset: 0 });
    await animationFrame();
    expect(getContent(el)).toBe(
        '<p>\ufeff<a href="http://test.test/" class="o_link_in_selection">[]\ufeffabc\ufeff</a>\ufeff</p>'
    );
});
