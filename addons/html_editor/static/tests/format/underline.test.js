import { describe, expect, test } from "@odoo/hoot";
import { tick } from "@odoo/hoot-mock";
import { press } from "@odoo/hoot-dom";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupEditor, testEditor } from "../_helpers/editor";
import { getContent } from "../_helpers/selection";
import {
    insertText,
    italic,
    simulateArrowKeyPress,
    tripleClick,
    underline,
    undo,
} from "../_helpers/user_actions";
import { unformat } from "../_helpers/format";

test("should make a few characters underline", async () => {
    await testEditor({
        contentBefore: `<p>ab[cde]fg</p>`,
        stepFunction: underline,
        contentAfter: `<p>ab<u>[cde]</u>fg</p>`,
    });
});

test("should make a few characters not underline", async () => {
    await testEditor({
        contentBefore: `<p><u>ab[cde]fg</u></p>`,
        stepFunction: underline,
        contentAfter: `<p><u>ab</u>[cde]<u>fg</u></p>`,
    });
});

test("should make two paragraphs underline", async () => {
    await testEditor({
        contentBefore: "<p>[abc</p><p>def]</p>",
        stepFunction: underline,
        contentAfter: `<p><u>[abc</u></p><p><u>def]</u></p>`,
    });
});

test("should make two paragraphs not underline", async () => {
    await testEditor({
        contentBefore: `<p><u>[abc</u></p><p><u>def]</u></p>`,
        stepFunction: underline,
        contentAfter: "<p>[abc</p><p>def]</p>",
    });
});

test("should make qweb tag underline", async () => {
    await testEditor({
        contentBefore: `<div><p t-esc="'Test'" contenteditable="false">[Test]</p></div>`,
        stepFunction: underline,
        contentAfter: `<div>[<p t-esc="'Test'" contenteditable="false" style="text-decoration-line: underline;">Test</p>]</div>`,
    });
});

test("should make a whole heading underline after a triple click", async () => {
    await testEditor({
        contentBefore: `<h1>[ab</h1><p>]cd</p>`,
        stepFunction: async (editor) => {
            await tripleClick(editor.editable.querySelector("h1"));
            underline(editor);
        },
        contentAfter: `<h1><u>[ab]</u></h1><p>cd</p>`,
    });
});

test("should make a whole heading not underline after a triple click", async () => {
    const { el, editor } = await setupEditor(`<h1><u>ab</u></h1><p>cd</p>`);
    await tripleClick(el.querySelector("h1"));
    underline(editor);
    expect(getContent(el)).toBe(`<h1>[ab]</h1><p>cd</p>`);
});

test("should make a selection starting with underline text fully underline", async () => {
    await testEditor({
        contentBefore: `<p><u>[ab</u></p><p>c]d</p>`,
        stepFunction: underline,
        contentAfter: `<p><u>[ab</u></p><p><u>c]</u>d</p>`,
    });
});

test("should make a selection with underline text in the middle fully underline", async () => {
    await testEditor({
        contentBefore: `<p>[a<u>b</u></p><p><u>c</u>d]e</p>`,
        stepFunction: underline,
        contentAfter: `<p><u>[ab</u></p><p><u>cd]</u>e</p>`,
    });
});

test("should make a selection ending with underline text fully underline", async () => {
    await testEditor({
        // @phoenix content adapted to make it valid html
        contentBefore: `<p>[ab</p><p><u>c]d</u></p>`,
        stepFunction: underline,
        contentAfter: `<p><u>[ab</u></p><p><u>c]d</u></p>`,
    });
});

test("should get ready to type in underline", async () => {
    await testEditor({
        contentBefore: `<p>ab[]cd</p>`,
        stepFunction: underline,
        contentAfterEdit: `<p>ab<u data-oe-zws-empty-inline="">[]\u200B</u>cd</p>`,
        contentAfter: `<p>ab[]cd</p>`,
    });
});

test("should get ready to type in not underline", async () => {
    await testEditor({
        contentBefore: `<p><u>ab[]cd</u></p>`,
        stepFunction: underline,
        contentAfterEdit: `<p><u>ab</u><span data-oe-zws-empty-inline="">[]\u200B</span><u>cd</u></p>`,
        contentAfter: `<p><u>ab[]cd</u></p>`,
    });
});

test("should not format non-editable text (underline)", async () => {
    await testEditor({
        contentBefore: '<p>[a</p><p contenteditable="false">b</p><p>c]</p>',
        stepFunction: underline,
        contentAfter: `<p><u>[a</u></p><p contenteditable="false">b</p><p><u>c]</u></p>`,
    });
});

test("should make a few characters underline inside table (underline)", async () => {
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
        stepFunction: underline,
        contentAfterEdit: unformat(`
            <table class="table table-bordered o_table o_selected_table">
                <tbody>
                    <tr>
                        <td class="o_selected_td"><p><u>[abc</u></p></td>
                        <td><p><br></p></td>
                        <td><p><br></p></td>
                    </tr>
                    <tr>
                        <td class="o_selected_td"><p><u>def</u></p></td>
                        <td><p><br></p></td>
                        <td><p><br></p></td>
                    </tr>
                    <tr>
                        <td class="o_selected_td"><p><u>]<br></u></p></td>
                        <td><p><br></p></td>
                        <td><p><br></p></td>
                    </tr>
                </tbody>
            </table>`),
    });
});

describe("with strikeThrough", () => {
    test("should get ready to write in strikeThrough without underline (underline was first)", async () => {
        await testEditor({
            contentBefore: `<p>ab<u><s>cd[]ef</s></u></p>`,
            stepFunction: underline,
            contentAfterEdit: `<p>ab<u><s>cd</s></u><s data-oe-zws-empty-inline="">[]\u200b</s><u><s>ef</s></u></p>`,
            contentAfter: `<p>ab<u><s>cd[]ef</s></u></p>`,
        });
    });

    test("should restore underline after removing it (collapsed, strikeThrough)", async () => {
        await testEditor({
            contentBefore: `<p>ab<u><s>cd</s></u><s data-oe-zws-empty-inline="">\u200b[]</s><u><s>ef</s></u></p>`,
            stepFunction: underline,
            contentAfterEdit: `<p>ab<u><s>cd</s></u><s data-oe-zws-empty-inline=""><u data-oe-zws-empty-inline="">[]\u200b</u></s><u><s>ef</s></u></p>`,
            contentAfter: `<p>ab<u><s>cd[]ef</s></u></p>`,
        });
    });

    test("should remove underline after restoring it after removing it (collapsed, strikeThrough)", async () => {
        await testEditor({
            contentBefore: `<p>ab<u><s>cd</s></u><s><u>[]\u200b</u></s><u><s>ef</s></u></p>`,
            stepFunction: underline,
            contentAfterEdit: `<p>ab<u><s>cd</s></u><s data-oe-zws-empty-inline="">[]\u200b</s><u><s>ef</s></u></p>`,
            contentAfter: `<p>ab<u><s>cd[]ef</s></u></p>`,
        });
    });

    test("should remove underline after restoring it and writing after removing it (collapsed, strikeThrough)", async () => {
        await testEditor({
            contentBefore: `<p>ab<u><s>cd</s></u><s><u>ghi[]</u></s><u><s>ef</s></u></p>`,
            stepFunction: underline,
            contentAfterEdit: `<p>ab<u><s>cd</s></u><s><u>ghi</u></s><s data-oe-zws-empty-inline="">[]\u200b</s><u><s>ef</s></u></p>`,
            // The reason the cursor is after the tag <s> is because when the editor get's cleaned, the zws tag gets deleted.
            contentAfter: `<p>ab<u><s>cd</s></u><s><u>ghi</u></s>[]<u><s>ef</s></u></p>`,
        });
    });

    test("should remove underline, write, restore underline, write, remove underline again, write (collapsed, strikeThrough)", async () => {
        await testEditor({
            contentBefore: `<p>ab<u><s>cd[]ef</s></u></p>`,
            stepFunction: async (editor) => {
                /** @todo fix warnings */
                patchWithCleanup(console, { warn: () => {} });

                underline(editor);
                await insertText(editor, "A");
                underline(editor);
                await insertText(editor, "B");
                underline(editor);
                await insertText(editor, "C");
            },
            contentAfterEdit: `<p>ab<u><s>cd</s></u><s>A<u>B</u>C[]</s><u><s>ef</s></u></p>`,
        });
    });

    test("should remove only underline decoration on a span", async () => {
        await testEditor({
            contentBefore: `<p><span style="text-decoration: underline line-through;">[a]</span></p>`,
            stepFunction: underline,
            contentAfter: `<p><span style="text-decoration: line-through;">[a]</span></p>`,
        });
    });
});

describe("with italic", () => {
    test("should get ready to write in italic and underline", async () => {
        await testEditor({
            contentBefore: `<p>ab[]cd</p>`,
            stepFunction: async (editor) => {
                italic(editor);
                underline(editor);
            },
            contentAfterEdit: `<p>ab<em data-oe-zws-empty-inline=""><u data-oe-zws-empty-inline="">[]\u200b</u></em>cd</p>`,
            contentAfter: `<p>ab[]cd</p>`,
        });
    });

    test("should get ready to write in italic, after changing one's mind about underline (two consecutive at the end)", async () => {
        await testEditor({
            contentBefore: `<p>ab[]cd</p>`,
            stepFunction: async (editor) => {
                italic(editor);
                underline(editor);
                underline(editor);
            },
            contentAfterEdit: `<p>ab<em data-oe-zws-empty-inline="">[]\u200B</em>cd</p>`,
            contentAfter: `<p>ab[]cd</p>`,
        });
    });

    test("should get ready to write in italic, after changing one's mind about underline (separated by italic)", async () => {
        await testEditor({
            contentBefore: `<p>ab[]cd</p>`,
            stepFunction: async (editor) => {
                underline(editor);
                italic(editor);
                underline(editor);
            },
            contentAfterEdit: `<p>ab<em data-oe-zws-empty-inline="">[]\u200B</em>cd</p>`,
            contentAfter: `<p>ab[]cd</p>`,
        });
    });

    test("should get ready to write in italic, after changing one's mind about underline (two consecutive at the beginning)", async () => {
        await testEditor({
            contentBefore: `<p>ab[]cd</p>`,
            stepFunction: async (editor) => {
                underline(editor);
                underline(editor);
                italic(editor);
            },
            contentAfterEdit: `<p>ab<em data-oe-zws-empty-inline="">[]\u200B</em>cd</p>`,
            contentAfter: `<p>ab[]cd</p>`,
        });
    });

    test("should get ready to write in italic without underline (underline was first)", async () => {
        await testEditor({
            contentBefore: `<p>ab<u><em>cd[]ef</em></u></p>`,
            stepFunction: underline,
            contentAfterEdit: `<p>ab<u><em>cd</em></u><em data-oe-zws-empty-inline="">[]\u200b</em><u><em>ef</em></u></p>`,
            contentAfter: `<p>ab<u><em>cd[]ef</em></u></p>`,
        });
    });

    test("should restore underline after removing it (collapsed, italic)", async () => {
        await testEditor({
            contentBefore: `<p>ab<u><em>cd</em></u><em>[]\u200b</em><u><em>ef</em></u></p>`,
            stepFunction: underline,
            contentAfterEdit: `<p>ab<u><em>cd</em></u><em><u data-oe-zws-empty-inline="">[]\u200b</u></em><u><em>ef</em></u></p>`,
            contentAfter: `<p>ab<u><em>cd</em></u><em>[]</em><u><em>ef</em></u></p>`,
        });
    });

    test("should remove underline after restoring it after removing it (collapsed, italic)", async () => {
        await testEditor({
            contentBefore: `<p>ab<u><em>cd</em></u><em><u>[]\u200b</u></em><u><em>ef</em></u></p>`,
            stepFunction: underline,
            contentAfterEdit: `<p>ab<u><em>cd</em></u><em data-oe-zws-empty-inline="">[]\u200b</em><u><em>ef</em></u></p>`,
            contentAfter: `<p>ab<u><em>cd[]ef</em></u></p>`,
        });
    });

    test("should remove underline after restoring it and writing after removing it (collapsed, italic)", async () => {
        await testEditor({
            contentBefore: `<p>ab<u><em>cd</em></u><em><u>ghi[]</u></em><u><em>ef</em></u></p>`,
            stepFunction: underline,
            contentAfterEdit: `<p>ab<u><em>cd</em></u><em><u>ghi</u></em><em data-oe-zws-empty-inline="">[]\u200b</em><u><em>ef</em></u></p>`,
            // The reason the cursor is after the tag <s> is because when the editor get's cleaned, the zws tag gets deleted.
            contentAfter: `<p>ab<u><em>cd</em></u><em><u>ghi</u></em>[]<u><em>ef</em></u></p>`,
        });
    });

    test("should remove underline, write, restore underline, write, remove underline again, write (collapsed, italic)", async () => {
        await testEditor({
            contentBefore: `<p>ab<u><em>cd[]ef</em></u></p>`,
            stepFunction: async (editor) => {
                /** @todo fix warnings */
                patchWithCleanup(console, { warn: () => {} });

                underline(editor);
                await insertText(editor, "A");
                underline(editor);
                await insertText(editor, "B");
                underline(editor);
                await insertText(editor, "C");
            },
            contentAfter: `<p>ab<u><em>cd</em></u><em>A<u>B</u>C[]</em><u><em>ef</em></u></p>`,
        });
    });

    test("should remove empty underline tag when changing selection", async () => {
        const { editor, el } = await setupEditor("<p>ab[]cd</p>");

        underline(editor);
        await tick();
        expect(getContent(el)).toBe(`<p>ab<u data-oe-zws-empty-inline="">[]\u200B</u>cd</p>`);

        await simulateArrowKeyPress(editor, "ArrowLeft");
        await tick(); // await selectionchange
        expect(getContent(el)).toBe(`<p>a[]bcd</p>`);
    });
});

test("should not add history step for underline on collapsed selection", async () => {
    const { editor, el } = await setupEditor("<p>abcd[]</p>");

    patchWithCleanup(console, { warn: () => {} });

    // Collapsed formatting shortcuts (e.g. Ctrl+U) shouldn’t create a history
    // step. The empty inline tag is temporary: auto-cleaned if unused. We want
    // to avoid having a phantom step in the history.
    await press(["ctrl", "u"]);
    expect(getContent(el)).toBe(`<p>abcd<u data-oe-zws-empty-inline="">[]\u200B</u></p>`);

    await insertText(editor, "A");
    expect(getContent(el)).toBe(`<p>abcd<u>A[]</u></p>`);

    undo(editor);
    expect(getContent(el)).toBe(`<p>abcd[]</p>`);
});
