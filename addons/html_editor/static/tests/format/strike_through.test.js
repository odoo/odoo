import { expect, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "../_helpers/editor";
import { getContent, setSelection } from "../_helpers/selection";
import { s, span } from "../_helpers/tags";
import { insertText, strikeThrough, tripleClick } from "../_helpers/user_actions";
import { unformat } from "../_helpers/format";

test("should make a few characters strikeThrough", async () => {
    await testEditor({
        contentBefore: `<p>ab[cde]fg</p>`,
        stepFunction: strikeThrough,
        contentAfter: `<p>ab${s(`[cde]`)}fg</p>`,
    });
});

test("should make a few characters not strikeThrough", async () => {
    await testEditor({
        contentBefore: `<p>${s(`ab[cde]fg`)}</p>`,
        stepFunction: strikeThrough,
        contentAfter: `<p>${s(`ab`)}[cde]${s(`fg`)}</p>`,
    });
});

test("should make a few characters strikeThrough then remove style inside", async () => {
    await testEditor({
        contentBefore: `<p>ab[c d]ef</p>`,
        stepFunction: async (editor) => {
            strikeThrough(editor);
            const styleSpan = editor.editable.querySelector("s").childNodes[0];
            const selection = {
                anchorNode: styleSpan,
                anchorOffset: 1,
                focusNode: styleSpan,
                focusOffset: 2,
            };
            setSelection(selection);
            strikeThrough(editor);
        },
        contentAfter: `<p>ab<s>c</s>[ ]<s>d</s>ef</p>`,
    });
});

test("should make strikeThrough then more then remove", async () => {
    await testEditor({
        contentBefore: `<p>abc[ ]def</p>`,
        stepFunction: async (editor) => {
            strikeThrough(editor);
            const pElem = editor.editable.querySelector("p").childNodes;
            const selection = {
                anchorNode: pElem[0],
                anchorOffset: 2,
                focusNode: pElem[2],
                focusOffset: 1,
            };
            setSelection(selection);
            strikeThrough(editor);
        },
        contentAfter: `<p>ab${s(`[c d]`)}ef</p>`,
    });
    await testEditor({
        contentBefore: `<p>abc[ ]def</p>`,
        stepFunction: async (editor) => {
            strikeThrough(editor);
            const pElem = editor.editable.querySelector("p").childNodes;
            const selection = {
                anchorNode: pElem[0],
                anchorOffset: 2,
                focusNode: pElem[2],
                focusOffset: 1,
            };
            setSelection(selection);
            strikeThrough(editor);
            strikeThrough(editor);
        },
        contentAfter: `<p>ab[c d]ef</p>`,
    });
});

test("should make two paragraphs strikeThrough", async () => {
    await testEditor({
        contentBefore: "<p>[abc</p><p>def]</p>",
        stepFunction: strikeThrough,
        contentAfter: `<p>${s(`[abc`)}</p><p>${s(`def]`)}</p>`,
    });
});

test("should make two paragraphs not strikeThrough", async () => {
    await testEditor({
        contentBefore: `<p>${s(`[abc`)}</p><p>${s(`def]`)}</p>`,
        stepFunction: strikeThrough,
        contentAfter: "<p>[abc</p><p>def]</p>",
    });
});

test("should make qweb tag strikeThrough", async () => {
    await testEditor({
        contentBefore: `<div><p t-esc="'Test'" contenteditable="false">[Test]</p></div>`,
        stepFunction: strikeThrough,
        contentAfter: `<div>[<p t-esc="'Test'" contenteditable="false" style="text-decoration-line: line-through;">Test</p>]</div>`,
    });
});

test("should make a whole heading strikeThrough after a triple click", async () => {
    await testEditor({
        contentBefore: `<h1>[ab</h1><p>]cd</p>`,
        stepFunction: strikeThrough,
        contentAfter: `<h1>${s(`[ab]`)}</h1><p>cd</p>`,
    });
});

test("should make a whole heading not strikeThrough after a triple click", async () => {
    const { el, editor } = await setupEditor(`<h1>${s(`[ab`)}</h1><p>]cd</p>`);
    await tripleClick(el.querySelector("h1"));
    strikeThrough(editor);
    expect(getContent(el)).toBe(`<h1>[ab]</h1><p>cd</p>`);
});

test("should make a selection starting with strikeThrough text fully strikeThrough", async () => {
    await testEditor({
        contentBefore: `<p>${s(`[ab`)}</p><p>c]d</p>`,
        stepFunction: strikeThrough,
        contentAfter: `<p>${s(`[ab`)}</p><p>${s(`c]`)}d</p>`,
    });
});

test("should make a selection with strikeThrough text in the middle fully strikeThrough", async () => {
    await testEditor({
        contentBefore: `<p>[a${s(`b`)}</p><p>${s(`c`)}d]e</p>`,
        stepFunction: strikeThrough,
        contentAfter: `<p>${s(`[ab`)}</p><p>${s(`cd]`)}e</p>`,
    });
});

test("should make a selection ending with strikeThrough text fully strikeThrough", async () => {
    await testEditor({
        // @phoenix content adapted to make it valid html
        contentBefore: `<p>[ab</p><p>${s(`c]d`)}</p>`,
        stepFunction: strikeThrough,
        contentAfter: `<p>${s(`[ab`)}</p><p>${s(`c]d`)}</p>`,
    });
});

test("should get ready to type in strikeThrough", async () => {
    await testEditor({
        contentBefore: `<p>ab[]cd</p>`,
        stepFunction: strikeThrough,
        contentAfterEdit: `<p>ab${s(`[]\u200B`, "first")}cd</p>`,
        contentAfter: `<p>ab[]cd</p>`,
    });
});

test("should get ready to type in not underline", async () => {
    await testEditor({
        contentBefore: `<p>${s(`ab[]cd`)}</p>`,
        stepFunction: strikeThrough,
        contentAfterEdit: `<p>${s(`ab`)}${span(`[]\u200B`, "first")}${s(`cd`)}</p>`,
        contentAfter: `<p>${s(`ab[]cd`)}</p>`,
    });
});

test("should do nothing when a block already has a line-through decoration", async () => {
    await testEditor({
        contentBefore: `<p style="text-decoration: line-through;">a[b]c</p>`,
        stepFunction: strikeThrough,
        contentAfter: `<p style="text-decoration: line-through;">a[b]c</p>`,
    });
});

test("should insert before strikethrough (1)", async () => {
    await testEditor({
        contentBefore: `<p>d[a${s("bc]<br><br>")}</p>`,
        stepFunction: async (editor) => {
            await insertText(editor, "A");
        },
        contentAfter: `<p>dA[]${s(`<br><br>`)}</p>`,
    });
});
test("should insert before strikethrough (2)", async () => {
    await testEditor({
        contentBefore: `<p>[a${s("bc]<br><br>")}</p>`,
        stepFunction: async (editor) => {
            await insertText(editor, "A");
        },
        contentAfter: `<p>${s(`A[]<br><br>`)}</p>`,
    });
});

test("should not format non-editable text (strikeThrough)", async () => {
    await testEditor({
        contentBefore: '<p>[a</p><p contenteditable="false">b</p><p>c]</p>',
        stepFunction: strikeThrough,
        contentAfter: `<p>${s("[a")}</p><p contenteditable="false">b</p><p>${s("c]")}</p>`,
    });
});

test("should make a few characters strikeThrough inside table (strikeThrough)", async () => {
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
            </table>`
        ),
        stepFunction: strikeThrough,
        contentAfterEdit: unformat(`
            <table class="table table-bordered o_table o_selected_table">
                <tbody>
                    <tr>
                        <td class="o_selected_td"><p>${s(`[abc`)}</p></td>
                        <td><p><br></p></td>
                        <td><p><br></p></td>
                    </tr>
                    <tr>
                        <td class="o_selected_td"><p>${s(`def`)}</p></td>
                        <td><p><br></p></td>
                        <td><p><br></p></td>
                    </tr>
                    <tr>
                        <td class="o_selected_td"><p>${s(`]<br>`)}</p></td>
                        <td><p><br></p></td>
                        <td><p><br></p></td>
                    </tr>
                </tbody>
            </table>`
        ),
    });
});
