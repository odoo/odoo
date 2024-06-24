import { test } from "@odoo/hoot";
import { manuallyDispatchProgrammaticEvent, press } from "@odoo/hoot-dom";
import { testEditor } from "../_helpers/editor";
import { setSelection } from "../_helpers/selection";

async function insertSpace(editor) {
    manuallyDispatchProgrammaticEvent(editor.editable, "keydown", { key: " " });
    manuallyDispatchProgrammaticEvent(editor.editable, "input", {
        inputType: "insertText",
        data: " ",
    });
    const range = editor.document.getSelection().getRangeAt(0);
    if (!range.collapsed) {
        throw new Error("need to implement something... maybe");
    }
    let offset = range.startOffset;
    const node = range.startContainer;
    // mimic the behavior of the browser when inserting a &nbsp
    const twoSpace = " \u00A0";
    node.textContent = (
        node.textContent.slice(0, offset) +
        " " +
        node.textContent.slice(offset)
    ).replaceAll("  ", twoSpace);

    if (
        node.nextSibling &&
        node.nextSibling.textContent.startsWith(" ") &&
        node.textContent.endsWith(" ")
    ) {
        node.nextSibling.textContent = "\u00A0" + node.nextSibling.textContent.slice(1);
    }

    offset++;
    setSelection({
        anchorNode: node,
        anchorOffset: offset,
    });

    // KeyUpEvent is not required but is triggered like the browser would.
    manuallyDispatchProgrammaticEvent(editor.editable, "keyup", { key: " " });
}

/**
 * Automatic link creation when pressing Space, Enter or Shift+Enter after an url
 */
test("should transform url after space", async () => {
    await testEditor({
        contentBefore: "<p>a http://test.com b http://test.com[] c http://test.com d</p>",
        stepFunction: async (editor) => {
            insertSpace(editor);
        },
        contentAfter:
            '<p>a http://test.com b <a href="http://test.com">http://test.com</a> []&nbsp;c http://test.com d</p>',
    });
    await testEditor({
        contentBefore: "<p>http://test.com[]</p>",
        stepFunction: async (editor) => {
            // Setup: simulate multiple text nodes in a p: <p>"http://test" ".com"</p>
            editor.editable.firstChild.firstChild.splitText(11);
            // Action: insert space
            insertSpace(editor);
        },
        contentAfter: '<p><a href="http://test.com">http://test.com</a> []</p>',
    });
});

test("should transform url followed by punctuation characters after space", async () => {
    await testEditor({
        contentBefore: "<p>http://test.com.[]</p>",
        stepFunction: async (editor) => {
            insertSpace(editor);
        },
        contentAfter: '<p><a href="http://test.com">http://test.com</a>. []</p>',
    });
    await testEditor({
        contentBefore: "<p>test.com...[]</p>",
        stepFunction: (editor) => insertSpace(editor),
        contentAfter: '<p><a href="http://test.com">test.com</a>... []</p>',
    });
    await testEditor({
        contentBefore: "<p>test.com,[]</p>",
        stepFunction: (editor) => insertSpace(editor),
        contentAfter: '<p><a href="http://test.com">test.com</a>, []</p>',
    });
    await testEditor({
        contentBefore: "<p>test.com,hello[]</p>",
        stepFunction: (editor) => insertSpace(editor),
        contentAfter: '<p><a href="http://test.com">test.com</a>,hello []</p>',
    });
    await testEditor({
        contentBefore: "<p>http://test.com[]</p>",
        stepFunction: async (editor) => {
            // Setup: simulate multiple text nodes in a p: <p>"http://test" ".com"</p>
            editor.editable.firstChild.firstChild.splitText(11);
            // Action: insert space
            insertSpace(editor);
        },
        contentAfter: '<p><a href="http://test.com">http://test.com</a> []</p>',
    });
});

test("should transform url after enter", async () => {
    await testEditor({
        contentBefore: "<p>a http://test.com b http://test.com[] c http://test.com d</p>",
        stepFunction: async (editor) => {
            press("enter");
            editor.dispatch("SPLIT_BLOCK");
        },
        contentAfter:
            '<p>a http://test.com b <a href="http://test.com">http://test.com</a></p><p>[]&nbsp;c http://test.com d</p>',
    });
});

test("should transform url after shift+enter", async () => {
    await testEditor({
        contentBefore: "<p>a http://test.com b http://test.com[] c http://test.com d</p>",
        stepFunction: async (editor) => {
            press(["shift", "enter"]);
            editor.dispatch("INSERT_LINEBREAK");
        },
        contentAfter:
            '<p>a http://test.com b <a href="http://test.com">http://test.com</a><br>[]&nbsp;c http://test.com d</p>',
    });
});

test("should not transform an email url after space", async () => {
    await testEditor({
        contentBefore: "<p>user@domain.com[]</p>",
        stepFunction: (editor) => insertSpace(editor),
        contentAfter: "<p>user@domain.com []</p>",
    });
});

test("should not transform url after two space", async () => {
    await testEditor({
        contentBefore: "<p>a http://test.com b http://test.com&nbsp;[] c http://test.com d</p>",
        stepFunction: (editor) => insertSpace(editor),
        contentAfter:
            "<p>a http://test.com b http://test.com&nbsp; []&nbsp;c http://test.com d</p>",
    });
});
