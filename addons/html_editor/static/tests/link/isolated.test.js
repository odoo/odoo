import { test } from "@odoo/hoot";
import { deleteBackward, insertText } from "../_helpers/user_actions";
import { testEditor } from "../_helpers/editor";
import { descendants } from "@html_editor/utils/dom_traversal";
import { tick } from "@odoo/hoot-mock";
import { setSelection } from "../_helpers/selection";

async function clickOnLink(editor) {
    throw new Error("clickOnLink not implemented");
    // const a = editor.editable.querySelector("a");
    // await click(a, { clientX: a.getBoundingClientRect().left + 5 });
    // return a;
}

test.todo("should restrict editing to link when clicked", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="#/"><span class="a">b</span></a></p>',
        stepFunction: async (editor) => {
            const a = await clickOnLink(editor);
            window.chai.expect(a.isContentEditable).to.be.equal(true);
        },
        contentAfter: '<p>a<a href="#/"><span class="a">b</span></a></p>',
    });
    // The following is a regression test, checking that the link
    // remains non-editable whenever the editable zone is contained by
    // the link.
    await testEditor(
        {
            contentBefore: '<p>a<a href="#/"><span class="a">b</span></a></p>',
            stepFunction: async (editor) => {
                const a = await clickOnLink(editor);
                window.chai.expect(a.isContentEditable).to.be.equal(false);
            },
            contentAfter:
                '<p>a<a href="#/"><span class="a" contenteditable="true">b</span></a></p>',
        },
        {
            isRootEditable: false,
            getContentEditableAreas: function (editor) {
                return [...editor.editable.querySelectorAll("a span")];
            },
        }
    );
});

test.todo("should keep isolated link after a delete", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="#/">b[]</a>c</p>',
        stepFunction: async (editor) => {
            await clickOnLink(editor);
            deleteBackward(editor);
        },
        contentAfterEdit:
            '<p>a\ufeff<a href="#/" class="o_link_in_selection">\ufeff[]\ufeff</a>\ufeffc</p>',
        contentAfter: "<p>a[]c</p>",
    });
});

test.todo("should keep isolated link after a delete and typing", async () => {
    await testEditor({
        contentBefore: '<p>a<a href="#/">b[]</a>c</p>',
        stepFunction: async (editor) => {
            await clickOnLink(editor);
            deleteBackward(editor);
            insertText(editor, "a");
            insertText(editor, "b");
            insertText(editor, "c");
        },
        contentAfter: '<p>a<a href="#/">abc[]</a>c</p>',
    });
});

test.todo("should delete the content from the link when popover is active", async () => {
    await testEditor({
        contentBefore: '<p><a href="#/">abc[]abc</a></p>',
        stepFunction: async (editor) => {
            await clickOnLink(editor);
            deleteBackward(editor);
            deleteBackward(editor);
            deleteBackward(editor);
            deleteBackward(editor);
        },
        contentAfter: '<p><a href="#/">[]abc</a></p>',
    });
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
