import { expect, test } from "@odoo/hoot";
import { manuallyDispatchProgrammaticEvent } from "@odoo/hoot-dom";
import { tick } from "@odoo/hoot-mock";
import { onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupEditor, testEditor } from "../_helpers/editor";
import { cleanLinkArtifacts } from "../_helpers/format";
import { getContent, setSelection } from "../_helpers/selection";
import { insertText, undo } from "../_helpers/user_actions";
import { expectElementCount } from "../_helpers/ui_expectations";

async function insertSpace(editor) {
    const keydownEvent = await manuallyDispatchProgrammaticEvent(editor.editable, "keydown", {
        key: " ",
    });
    if (keydownEvent.defaultPrevented) {
        return;
    }
    // InputEvent is required to simulate the insert text.
    const [beforeinputEvent] = await manuallyDispatchProgrammaticEvent(
        editor.editable,
        "beforeinput",
        {
            inputType: "insertText",
            data: " ",
        }
    );
    if (beforeinputEvent.defaultPrevented) {
        return;
    }
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

    const [inputEvent] = await manuallyDispatchProgrammaticEvent(editor.editable, "input", {
        inputType: "insertText",
        data: " ",
    });
    if (inputEvent.defaultPrevented) {
        return;
    }
    // KeyUpEvent is not required but is triggered like the browser would.
    await manuallyDispatchProgrammaticEvent(editor.editable, "keyup", { key: " " });
}

/**
 * Automatic link creation when pressing Space, Enter or Shift+Enter after an url
 */
test("should transform url after space (1)", async () => {
    await testEditor({
        contentBefore: "<p>a http://test.com b http://test.com[] c http://test.com d</p>",
        stepFunction: async (editor) => {
            await insertSpace(editor);
        },
        contentAfter:
            '<p>a http://test.com b <a href="http://test.com">http://test.com</a>&nbsp;[] c http://test.com d</p>',
    });
});
test("should transform url after space (2)", async () => {
    await testEditor({
        contentBefore: "<p>http://test.com[]</p>",
        stepFunction: async (editor) => {
            // Setup: simulate multiple text nodes in a p: <p>"http://test" ".com"</p>
            editor.editable.firstChild.firstChild.splitText(11);

            /** @todo fix warnings */
            patchWithCleanup(console, { warn: () => {} });

            // Action: insert space
            await insertSpace(editor);
        },
        contentAfter: '<p><a href="http://test.com">http://test.com</a>&nbsp;[]</p>',
    });
});

test("should transform url followed by punctuation characters after space (1)", async () => {
    await testEditor({
        contentBefore: "<p>http://test.com.[]</p>",
        stepFunction: async (editor) => {
            await insertSpace(editor);
        },
        contentAfter: '<p><a href="http://test.com">http://test.com</a>.&nbsp;[]</p>',
    });
});
test("should transform url followed by punctuation characters after space (2)", async () => {
    await testEditor({
        contentBefore: "<p>test.com...[]</p>",
        stepFunction: (editor) => insertSpace(editor),
        contentAfter: '<p><a href="https://test.com">test.com</a>...&nbsp;[]</p>',
    });
});
test("should transform url followed by punctuation characters after space (3)", async () => {
    await testEditor({
        contentBefore: "<p>test.com,[]</p>",
        stepFunction: (editor) => insertSpace(editor),
        contentAfter: '<p><a href="https://test.com">test.com</a>,&nbsp;[]</p>',
    });
});
test("should transform url followed by punctuation characters after space (4)", async () => {
    await testEditor({
        contentBefore: "<p>test.com,hello[]</p>",
        stepFunction: (editor) => insertSpace(editor),
        contentAfter: '<p><a href="https://test.com">test.com</a>,hello&nbsp;[]</p>',
    });
});
test("should transform url followed by punctuation characters after space (5)", async () => {
    await testEditor({
        contentBefore: "<p>http://test.com[]</p>",
        stepFunction: async (editor) => {
            // Setup: simulate multiple text nodes in a p: <p>"http://test" ".com"</p>
            editor.editable.firstChild.firstChild.splitText(11);

            /** @todo fix warnings */
            patchWithCleanup(console, { warn: () => {} });

            // Action: insert space
            await insertSpace(editor);
        },
        contentAfter: '<p><a href="http://test.com">http://test.com</a>&nbsp;[]</p>',
    });
});

test("should transform url after enter", async () => {
    await testEditor({
        contentBefore: "<p>a http://test.com b http://test.com[] c http://test.com d</p>",
        stepFunction: async (editor) => {
            // Simulate "Enter"
            await manuallyDispatchProgrammaticEvent(editor.editable, "beforeinput", {
                inputType: "insertParagraph",
            });
        },
        contentAfter:
            '<p>a http://test.com b <a href="http://test.com">http://test.com</a></p><p>[]&nbsp;c http://test.com d</p>',
    });
});

test("should transform url after shift+enter", async () => {
    await testEditor({
        contentBefore: "<p>a http://test.com b http://test.com[] c http://test.com d</p>",
        stepFunction: async (editor) => {
            // Simulate "Shift + Enter"
            await manuallyDispatchProgrammaticEvent(editor.editable, "beforeinput", {
                inputType: "insertLineBreak",
            });
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

test("transform text url into link and undo it", async () => {
    const { el, editor } = await setupEditor(`<p>[]</p>`);
    await insertText(editor, "www.abc.jpg ");
    expect(cleanLinkArtifacts(getContent(el))).toBe(
        '<p><a href="https://www.abc.jpg">www.abc.jpg</a>&nbsp;[]</p>'
    );

    undo(editor);
    expect(cleanLinkArtifacts(getContent(el))).toBe(
        '<p><a href="https://www.abc.jpg">www.abc.jpg</a>[]</p>'
    );

    undo(editor);
    expect(cleanLinkArtifacts(getContent(el))).toBe("<p>www.abc.jpg[]</p>");
});

test("should show replace URL button if link is created by transformation", async () => {
    onRpc("/html_editor/link_preview_external", () => ({
        og_description:
            "From ERP to CRM, eCommerce and CMS. Download Odoo or use it in the cloud. Grow Your Business.",
        og_image: "https://www.odoo.com/web/image/41207129-1abe7a15/homepage-seo.png",
        og_title: "Open Source ERP and CRM | Odoo",
        og_type: "website",
        og_site_name: "Odoo",
        source_url: "https://odoo.com",
    }));
    const { editor } = await setupEditor(`<p>[]</p>`);
    await insertText(editor, "https://odoo.com ");
    const link = document.querySelector("a");
    setSelection({
        anchorNode: link,
        anchorOffset: 0,
    });
    await tick();
    await expectElementCount(".o-we-linkpopover", 1);
    expect("button.o_we_replace_title_btn").toHaveCount(1);
});
