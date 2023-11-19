import { test } from "@odoo/hoot";
import { deleteBackward, insertText } from "../_helpers/user_actions";
import { testEditor } from "../_helpers/editor";

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
            '<p>a<a href="#/" data-oe-zws-empty-inline="" class="o_link_in_selection">' +
            '<span data-o-link-zws="start" contenteditable="false">\u200B</span>' + // start zws
            "[]\u200B" + // content: empty inline zws
            '<span data-o-link-zws="end">\u200B</span>' + // end zws
            "</a>" +
            '<span data-o-link-zws="after" contenteditable="false">\u200B</span>' + // after zws
            "c</p>",
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
