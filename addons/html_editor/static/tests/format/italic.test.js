import { expect, test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupEditor, testEditor } from "../_helpers/editor";
import { getContent } from "../_helpers/selection";
import { em, span } from "../_helpers/tags";
import {
    italic,
    tripleClick,
    simulateArrowKeyPress,
    insertText,
    undo,
} from "../_helpers/user_actions";
import { unformat } from "../_helpers/format";
import { tick } from "@odoo/hoot-mock";

test("should make a few characters italic", async () => {
    await testEditor({
        contentBefore: `<p>ab[cde]fg</p>`,
        stepFunction: italic,
        contentAfter: `<p>ab${em(`[cde]`)}fg</p>`,
    });
});

test("should make a few characters not italic", async () => {
    await testEditor({
        contentBefore: `<p>${em(`ab[cde]fg`)}</p>`,
        stepFunction: italic,
        contentAfter: `<p>${em(`ab`)}[cde]${em(`fg`)}</p>`,
    });
});

test("should make two paragraphs italic", async () => {
    await testEditor({
        contentBefore: "<p>[abc</p><p>def]</p>",
        stepFunction: italic,
        contentAfter: `<p>${em(`[abc`)}</p><p>${em(`def]`)}</p>`,
    });
});

test("should make two paragraphs not italic", async () => {
    await testEditor({
        contentBefore: `<p>${em(`[abc`)}</p><p>${em(`def]`)}</p>`,
        stepFunction: italic,
        contentAfter: `<p>[abc</p><p>def]</p>`,
    });
});

test("should make qweb tag italic", async () => {
    await testEditor({
        contentBefore: `<div><p t-esc="'Test'" contenteditable="false">[Test]</p></div>`,
        stepFunction: italic,
        contentAfter: `<div>[<p t-esc="'Test'" contenteditable="false" style="font-style: italic;">Test</p>]</div>`,
    });
});

test.tags("desktop");
test("should make a whole heading italic after a triple click", async () => {
    await testEditor({
        contentBefore: `<h1>ab</h1><p>cd</p>`,
        stepFunction: async (editor) => {
            await tripleClick(editor.editable.querySelector("h1"));
            italic(editor);
        },
        contentAfter: `<h1>${em(`[ab]`)}</h1><p>cd</p>`,
    });
});

test.tags("desktop");
test("should make a whole heading not italic after a triple click", async () => {
    await testEditor({
        contentBefore: `<h1>${em(`ab`)}</h1><p>cd</p>`,
        stepFunction: async (editor) => {
            await tripleClick(editor.editable.querySelector("h1"));
            italic(editor);
        },
        contentAfter: `<h1>[ab]</h1><p>cd</p>`,
    });
});

test("should make a selection starting with italic text fully italic", async () => {
    await testEditor({
        contentBefore: `<p>${em(`[ab`)}</p><p>c]d</p>`,
        stepFunction: italic,
        contentAfter: `<p>${em(`[ab`)}</p><p>${em(`c]`)}d</p>`,
    });
});

test("should make a selection with italic text in the middle fully italic", async () => {
    await testEditor({
        contentBefore: `<p>[a${em(`b`)}</p><p>${em(`c`)}d]e</p>`,
        stepFunction: italic,
        contentAfter: `<p>${em(`[ab`)}</p><p>${em(`cd]`)}e</p>`,
    });
});

test("should make a selection ending with italic text fully italic", async () => {
    await testEditor({
        contentBefore: `<p>[ab</p><p>${em(`c]d`)}</p>`,
        stepFunction: italic,
        contentAfter: `<p>${em(`[ab`)}</p><p>${em(`c]d`)}</p>`,
    });
});

test("should make two paragraphs (separated with whitespace) italic", async () => {
    await testEditor({
        contentBefore: `
            <p>[abc</p>
            <p>def]</p>
        `,
        stepFunction: italic,
        contentAfter: `
            <p><em>[abc</em></p>
            <p><em>def]</em></p>
        `,
    });
});

test("should make two paragraphs (separated with whitespace) not italic", async () => {
    await testEditor({
        contentBefore: `
            <p><em>[abc</em></p>
            <p><em>def]</em></p>
        `,
        stepFunction: italic,
        contentAfter: `
            <p>[abc</p>
            <p>def]</p>
        `,
    });
});

test("should make two paragraphs (separated with whitespace) italic, then not italic", async () => {
    await testEditor({
        contentBefore: `
            <p>[abc</p>
            <p>def]</p>
        `,
        stepFunction: async (editor) => {
            italic(editor);
            expect(getContent(editor.editable)).toBe(`
            <p><em>[abc</em></p>
            <p><em>def]</em></p>
        `);
            italic(editor);
        },
        contentAfter: `
            <p>[abc</p>
            <p>def]</p>
        `,
    });
});

test("should get ready to type in italic", async () => {
    await testEditor({
        contentBefore: `<p>ab[]cd</p>`,
        stepFunction: italic,
        contentAfterEdit: `<p>ab${em(`[]\u200B`, "first")}cd</p>`,
        contentAfter: `<p>ab[]cd</p>`,
    });
});

test("should get ready to type in not italic", async () => {
    await testEditor({
        contentBefore: `<p>${em(`ab[]cd`)}</p>`,
        stepFunction: italic,
        contentAfterEdit: `<p>${em(`ab`)}${span(`[]\u200B`, "first")}${em(`cd`)}</p>`,
        contentAfter: `<p>${em(`ab[]cd`)}</p>`,
    });
});

test("should not format non-editable text (italic)", async () => {
    await testEditor({
        contentBefore: '<p>[a</p><p contenteditable="false">b</p><p>c]</p>',
        stepFunction: italic,
        contentAfter: `<p>${em("[a")}</p><p contenteditable="false">b</p><p>${em("c]")}</p>`,
    });
});

test("should remove empty italic tag when changing selection", async () => {
    const { editor, el } = await setupEditor("<p>ab[]cd</p>");

    italic(editor);
    await tick();
    expect(getContent(el)).toBe(`<p>ab${em("[]\u200B", "first")}cd</p>`);

    await simulateArrowKeyPress(editor, "ArrowLeft");
    await tick(); // await selectionchange
    expect(getContent(el)).toBe(`<p>a[]bcd</p>`);
});

test("should make a few characters italic inside table (italic)", async () => {
    await testEditor({
        contentBefore: unformat(`
            <table class="table table-bordered o_table o_selected_table">
                <tbody>
                    <tr>
                        <td class="o_selected_td"><p>[abc</p></td>
                        <td><p><br></p></td>
                        <td><p><br></p></td>
                    </tr>
                    <tr>
                        <td class="o_selected_td"><p>def</p></td>
                        <td><p><br></p></td>
                        <td><p><br></p></td>
                    </tr>
                    <tr>
                        <td class="o_selected_td"><p>]<br></p></td>
                        <td><p><br></p></td>
                        <td><p><br></p></td>
                    </tr>
                </tbody>
            </table>`),
        stepFunction: italic,
        contentAfterEdit: unformat(`
            <p data-selection-placeholder=""><br></p>
            <table class="table table-bordered o_table o_selected_table">
                <tbody>
                    <tr>
                        <td class="o_selected_td"><p>${em(`[abc`)}</p></td>
                        <td><p><br></p></td>
                        <td><p><br></p></td>
                    </tr>
                    <tr>
                        <td class="o_selected_td"><p>${em(`def`)}</p></td>
                        <td><p><br></p></td>
                        <td><p><br></p></td>
                    </tr>
                    <tr>
                        <td class="o_selected_td"><p>${em(`]<br>`)}</p></td>
                        <td><p><br></p></td>
                        <td><p><br></p></td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`),
    });
});

test("should not add history step for italic on collapsed selection", async () => {
    const { editor, el } = await setupEditor("<p>abcd[]</p>");

    patchWithCleanup(console, { warn: () => {} });

    // Collapsed formatting shortcuts (e.g. Ctrl+I) shouldn’t create a history
    // step. The empty inline tag is temporary: auto-cleaned if unused. We want
    // to avoid having a phantom step in the history.
    await press(["ctrl", "i"]);
    expect(getContent(el)).toBe(`<p>abcd${em("[]\u200B", "first")}</p>`);

    await insertText(editor, "A");
    expect(getContent(el)).toBe(`<p>abcd${em("A[]")}</p>`);

    undo(editor);
    expect(getContent(el)).toBe(`<p>abcd[]</p>`);
});
