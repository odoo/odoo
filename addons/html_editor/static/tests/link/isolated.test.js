import { expect, test } from "@odoo/hoot";
import { deleteBackward, insertText } from "../_helpers/user_actions";
import { setupEditor, testEditor } from "../_helpers/editor";
import { descendants } from "@html_editor/utils/dom_traversal";
import { tick } from "@odoo/hoot-mock";
import { getContent, setSelection } from "../_helpers/selection";
import { cleanLinkArtifacts } from "../_helpers/format";
import { waitFor } from "@odoo/hoot-dom";

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
    await waitFor(".o-we-linkpopover");
    expect(".o-we-linkpopover").toHaveCount(1);
    deleteBackward(editor);
    deleteBackward(editor);
    deleteBackward(editor);
    const content = getContent(el);
    expect(content).toBe(
        '<p>\ufeff<a href="#/" class="o_link_in_selection">\ufeff[]abc\ufeff</a>\ufeff</p>'
    );
    expect(cleanLinkArtifacts(content)).toBe('<p><a href="#/">[]abc</a></p>');
});

test("should zwnbsp-pad simple text link", async () => {
    const removeZwnbsp = (editor) => {
        for (const descendant of descendants(editor.editable)) {
            if (descendant.nodeType === Node.TEXT_NODE && descendant.textContent === "\ufeff") {
                descendant.remove();
            }
        }
    };
    await testEditor({
        contentBefore: '<p>a[]<a href="#/">bc</a>d</p>',
        contentBeforeEdit: '<p>a[]\ufeff<a href="#/">\ufeffbc\ufeff</a>\ufeffd</p>',
        stepFunction: async (editor) => {
            removeZwnbsp(editor);
            const p = editor.editable.querySelector("p");
            // set the selection via the parent
            setSelection({ anchorNode: p, anchorOffset: 1 });
            // insert the zwnbsp again
            editor.dispatch("NORMALIZE", { node: editor.editable });
        },
        contentAfterEdit: '<p>a\ufeff[]<a href="#/">\ufeffbc\ufeff</a>\ufeffd</p>',
    });
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
            editor.dispatch("NORMALIZE", { node: editor.editable });
        },
        contentAfterEdit:
            '<p>a\ufeff<a href="#/" class="o_link_in_selection">\ufeff[]bc\ufeff</a>\ufeffd</p>',
    });
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
            editor.dispatch("NORMALIZE", { node: editor.editable });
        },
        contentAfterEdit:
            '<p>a\ufeff<a href="#/" class="o_link_in_selection">\ufeffb[]c\ufeff</a>\ufeffd</p>',
    });
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
            editor.dispatch("NORMALIZE", { node: editor.editable });
        },
        contentAfterEdit:
            '<p>a\ufeff<a href="#/" class="o_link_in_selection">\ufeffbc[]\ufeff</a>\ufeffd</p>',
    });
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
            editor.dispatch("NORMALIZE", { node: editor.editable });
        },
        contentAfterEdit: '<p>a\ufeff<a href="#/">\ufeffbc\ufeff</a>\ufeff[]d</p>',
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
            '<p>a<a href="#/">[]<i style="display: flex;" class="fa fa-star" contenteditable="false">\u200b</i></a>b</p>',
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
