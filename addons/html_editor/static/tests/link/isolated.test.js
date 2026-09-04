import { click, describe, expect, test } from "@odoo/hoot";
import { deleteBackward, insertText } from "../_helpers/user_actions";
import { setupEditor, testEditor } from "../_helpers/editor";
import { descendants } from "@html_editor/utils/dom_traversal";
import { tick } from "@odoo/hoot-mock";
import { getContent, setSelection } from "../_helpers/selection";
import { cleanLinkArtifacts } from "../_helpers/format";
import { dispatchNormalize } from "../_helpers/dispatch";
import { expectElementCount } from "../_helpers/ui_expectations";
import { animationFrame } from "@odoo/hoot-dom";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

test("should pad a link with ZWNBSPs and add visual indication", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="#/">b</a>c</p>',
        contentBeforeEdit: '<p>a\ufeff<a href="#/">\ufeffb\ufeff</a>\ufeffc</p>',
        stepFunction: async (editor) => {
            setSelection({ anchorNode: editor.editable.querySelector("a"), anchorOffset: 1 });
            await tick();
        },
        contentAfterEdit:
            '<p>a\ufeff<a href="#/" class="o_link_in_selection">\ufeff[]b\ufeff</a>\ufeffc</p>',
        contentAfter: '<p>a<a href="#/">[]b</a>c</p>',
    });
});

test("should pad a link with ZWNBSPs and add visual indication (2)", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="#/"><span class="a">b</span></a></p>',
        contentBeforeEdit:
            '<p>a\ufeff<a href="#/">\ufeff<span class="a">b</span>\ufeff</a>\ufeff</p>',
        stepFunction: async (editor) => {
            setSelection({ anchorNode: editor.editable.querySelector("a span"), anchorOffset: 0 });
            await tick();
        },
        contentAfterEdit:
            '<p>a\ufeff<a href="#/" class="o_link_in_selection">\ufeff<span class="a">[]b</span>\ufeff</a>\ufeff</p>',
        contentAfter: '<p>a<a href="#/"><span class="a">[]b</span></a></p>',
    });
});

test("should keep link padded with ZWNBSPs after a delete", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="#/">b[]</a>c</p>',
        stepFunction: deleteBackward,
        contentAfterEdit:
            '<p>a\ufeff<a href="#/" class="o_link_in_selection">\ufeff[]\ufeff</a>\ufeffc</p>',
        contentAfter: "<p>a[]c</p>",
    });
});

test("should keep isolated link after a delete and typing", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="#/">b[]</a>c</p>',
        stepFunction: async (editor) => {
            deleteBackward(editor);
            await insertText(editor, "a");
            await insertText(editor, "b");
            await insertText(editor, "c");
        },
        contentAfter: '<p>a<a href="#/">abc[]</a>c</p>',
    });
});

test("should delete the content from the link when popover is active", async () => {
    const { editor, el } = await setupEditor('<p><a href="#/">abc[]abc</a></p>');
    await expectElementCount(".o-we-linkpopover", 1);
    deleteBackward(editor);
    deleteBackward(editor);
    deleteBackward(editor);
    const content = getContent(el);
    expect(content).toBe(
        '<p>\ufeff<a href="#/" class="o_link_in_selection">\ufeff[]abc\ufeff</a>\ufeff</p>'
    );
    expect(cleanLinkArtifacts(content)).toBe('<p><a href="#/">[]abc</a></p>');
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
            contentBefore: '<p>a<a href="#/">[]bc</a>d</p>',
            contentBeforeEdit:
                '<p>a\ufeff<a href="#/" class="o_link_in_selection">\ufeff[]bc\ufeff</a>\ufeffd</p>',
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
                '<p>a\ufeff<a href="#/" class="o_link_in_selection">\ufeff[]bc\ufeff</a>\ufeffd</p>',
        });
    });
    test("should zwnbsp-pad simple text link (3)", async () => {
        await testEditor({
            contentBefore: '<p>a<a href="#/">b[]</a>d</p>',
            contentBeforeEdit:
                '<p>a\ufeff<a href="#/" class="o_link_in_selection">\ufeffb[]\ufeff</a>\ufeffd</p>',
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
                '<p>a\ufeff<a href="#/" class="o_link_in_selection">\ufeffb[]c\ufeff</a>\ufeffd</p>',
        });
    });
    test("should zwnbsp-pad simple text link (4)", async () => {
        await testEditor({
            contentBefore: '<p>a<a href="#/">bc[]</a>d</p>',
            contentBeforeEdit:
                '<p>a\ufeff<a href="#/" class="o_link_in_selection">\ufeffbc[]\ufeff</a>\ufeffd</p>',
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
                '<p>a\ufeff<a href="#/" class="o_link_in_selection">\ufeffbc[]\ufeff</a>\ufeffd</p>',
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
        contentBefore: '<p>a<a href="#/" class="nav-link">[]b</a>c</p>',
        contentBeforeEdit: '<p>a<a href="#/" class="nav-link">[]b</a>c</p>',
    });
});

test("should not zwnbsp-pad in nav", async () => {
    await testEditor({
        contentBefore: '<nav>a<a href="#/">[]b</a>c</nav>',
        contentBeforeEdit: '<nav>a<a href="#/">[]b</a>c</nav>',
    });
});

test("should not zwnbsp-pad link with block fontawesome", async () => {
    await testEditor({
        contentBefore:
            '<p>a<a href="#/">[]<i style="display: flex;" class="fa fa-star"></i></a>b</p>',
        contentBeforeEdit:
            '<p>a<a href="#/">\ufeff[]<i style="display: flex;" class="fa fa-star" contenteditable="false">\u200b</i>\ufeff</a>b</p>',
    });
});

test("should not zwnbsp-pad link with image", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="#/">[]<img style="display: inline;"></a>b</p>',
        contentBeforeEdit: '<p>a<a href="#/">[]<img style="display: inline;"></a>b</p>',
    });
});

test("should remove zwnbsp from middle of the link", async () => {
    await testEditor({
        contentBefore: '<p><a href="#/">content</a></p>',
        contentBeforeEdit: '<p>\ufeff<a href="#/">\ufeffcontent\ufeff</a>\ufeff</p>',
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
        contentBeforeEdit: '<p>\ufeff<a href="#/">\ufeffcontent\ufeff</a>\ufeff</p>',
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
            contentBefore: '<p><a class="btn">content</a></p>',
            contentBeforeEdit: '<p>\ufeff<a class="btn">\ufeffcontent\ufeff</a>\ufeff</p>',
        });
    });

    test("should not add visual indication to a button", async () => {
        await testEditor({
            contentBefore: '<p><a class="btn">[]content</a></p>',
            contentBeforeEdit: '<p>\ufeff<a class="btn">\ufeffcontent\ufeff</a>\ufeff</p>',
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

    test("should delete previous character without errors when backspacing with the cursor in between a zwnbsp and the left edge of a button", async () => {
        const { editor, el } = await setupEditor(
            '<p>before[]<a class="btn" href="#/">in</a>after</p>'
        );
        const p = el.querySelector("p");
        setSelection({ anchorNode: p, anchorOffset: 2 });
        await tick();
        expect(getContent(el)).toBe(
            '<p>before\ufeff[]<a class="btn" href="#/">\ufeffin\ufeff</a>\ufeffafter</p>'
        );
        deleteBackward(editor);
        expect(getContent(el)).toBe(
            '<p>befor[]\ufeff<a class="btn" href="#/">\ufeffin\ufeff</a>\ufeffafter</p>'
        );
    });
});

describe.tags("desktop");
describe("should position the cursor outside the link", () => {
    test("clicking at the end of block after a link", async () => {
        const { el } = await setupEditor('<p><a href="#/">test</a></p>');
        const a = el.querySelector("a");
        const rect = a.getBoundingClientRect();
        const clientX = rect.right + 1;
        const clientY = rect.top + rect.height / 2;
        patchWithCleanup(document, {
            caretPositionFromPoint: () => ({ offsetNode: a.firstChild.nextSibling, offset: 4 }),
        });
        await click(el, { clientX, clientY });
        await animationFrame();
        expect(getContent(el)).toBe('<p>\ufeff<a href="#/">\ufefftest\ufeff</a>\ufeff[]</p>');
    });

    test("clicking at the end of a link", async () => {
        const { el, editor } = await setupEditor('<p><a href="#/">test</a></p>');
        const a = el.querySelector("a");
        const rect = a.getBoundingClientRect();
        const clientX = rect.right - 1;
        const clientY = rect.top + rect.height / 2;
        patchWithCleanup(document, {
            caretPositionFromPoint: () => ({ offsetNode: a.firstChild.nextSibling, offset: 4 }),
        });
        let called = false;
        await click(a, { clientX, clientY });
        await animationFrame();
        // We should let the browser set the selection for this case
        const original = editor.shared.selection.setSelection.bind(editor.shared.selection);
        editor.shared.selection.setSelection = (...args) => {
            called = true;
            original(...args);
        };
        expect(called).toBe(false);
    });

    test("clicking at the end padding of the button", async () => {
        const { el, editor } = await setupEditor(
            '<p><a class="btn btn-primary" href="#/">test</a></p>'
        );
        const a = el.querySelector("a");
        const rect = a.getBoundingClientRect();
        const clientX = rect.right - 1;
        const clientY = rect.top + rect.height / 2;
        patchWithCleanup(document, {
            caretPositionFromPoint: () => ({ offsetNode: a.firstChild.nextSibling, offset: 4 }),
        });
        let called = false;
        await click(a, { clientX, clientY });
        await animationFrame();
        // We should let the browser set the selection for this case
        const original = editor.shared.selection.setSelection.bind(editor.shared.selection);
        editor.shared.selection.setSelection = (...args) => {
            called = true;
            original(...args);
        };
        expect(called).toBe(false);
    });

    test("clicking at the start padding of the button", async () => {
        const { el } = await setupEditor('<p><a class="btn btn-primary" href="#/">test</a></p>');
        const a = el.querySelector("a");
        const rect = a.getBoundingClientRect();
        const clientX = rect.left + 1;
        const clientY = rect.top + rect.height / 2;
        patchWithCleanup(document, {
            caretPositionFromPoint: () => ({ offsetNode: a.firstChild, offset: 0 }),
        });
        await click(a, { clientX, clientY });
        await animationFrame();
        expect(getContent(el)).toBe(
            '<p>\ufeff<a class="btn btn-primary" href="#/">\ufeff[]test\ufeff</a>\ufeff</p>'
        );
    });

    test("clicking at the end after the button", async () => {
        const { el } = await setupEditor('<p><a class="btn btn-primary" href="#/">test</a></p>');
        const a = el.querySelector("a");
        const rect = a.getBoundingClientRect();
        const clientX = rect.right + 1;
        const clientY = rect.top + rect.height / 2;
        patchWithCleanup(document, {
            caretPositionFromPoint: () => ({ offsetNode: a, offset: 3 }),
        });
        await click(a.parentElement, { clientX, clientY });
        await animationFrame();
        expect(getContent(el)).toBe(
            '<p>\ufeff<a class="btn btn-primary" href="#/">\ufefftest\ufeff</a>\ufeff[]</p>'
        );
    });
});
