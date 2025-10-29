import { describe, expect, test } from "@odoo/hoot";
import { waitFor, waitForNone, press, manuallyDispatchProgrammaticEvent } from "@odoo/hoot-dom";
import { setupEditor, testEditor } from "./_helpers/editor";
import { getContent } from "./_helpers/selection";
import { insertText, splitBlock } from "./_helpers/user_actions";

async function simulateEnter(editor) {
    press("enter");
    await manuallyDispatchProgrammaticEvent(editor.editable, "beforeinput", {
        inputType: "insertParagraph",
    });
}

describe("SplitBlock", () => {
    test("should force <br> in blockquote", async () => {
        await testEditor({
            contentBefore: "<blockquote>abc[]</blockquote>",
            stepFunction: splitBlock,
            contentAfter: "<blockquote>abc<br>[]<br></blockquote>",
        });
    });
    test("should force <br> in blockquote containing inline element", async () => {
        await testEditor({
            contentBefore: "<blockquote>ab<strong>c[]</strong></blockquote>",
            stepFunction: splitBlock,
            contentAfter: "<blockquote>ab<strong>c<br>[]<br></strong></blockquote>",
        });
    });
    test("should force <br> in empty blockquote", async () => {
        await testEditor({
            contentBefore: "<blockquote>[]<br></blockquote>",
            stepFunction: splitBlock,
            contentAfter: "<blockquote><br>[]<br></blockquote>",
        });
    });
    test("should insert a new paragraph within the blockquote", async () => {
        await testEditor({
            contentBefore: "<blockquote><p>abc</p><p>def[]</p></blockquote>",
            stepFunction: splitBlock,
            contentAfter: "<blockquote><p>abc</p><p>def</p><p>[]<br></p></blockquote>",
        });
    });
    test("should move an empty paragraph after the blockquote if at the end", async () => {
        await testEditor({
            contentBefore: "<blockquote><p>abc</p><p>def</p><p>[]<br></p></blockquote>",
            stepFunction: splitBlock,
            contentAfter: "<blockquote><p>abc</p><p>def</p></blockquote><p>[]<br></p>",
        });
    });
    test("should insert a new paragraph within the blockquote tag with rtl direction", async () => {
        await testEditor({
            contentBefore: `<blockquote dir="rtl">ab[]</blockquote>`,
            stepFunction: splitBlock,
            contentAfter: `<blockquote dir="rtl">ab<br>[]<br></blockquote>`,
        });
    });
    test("should insert a new paragraph within the blockquote tag with rtl direction (2)", async () => {
        await testEditor({
            contentBefore: `<blockquote><p dir="rtl">abc[]</p></blockquote>`,
            stepFunction: splitBlock,
            contentAfter: `<blockquote><p dir="rtl">abc</p><p dir="rtl">[]<br></p></blockquote>`,
        });
    });
    test("should move an empty paragraph after the blockquote with rtl direction if at the end", async () => {
        await testEditor({
            contentBefore: `<blockquote><p dir="rtl">abc</p><p dir="rtl">[]<br></p></blockquote>`,
            stepFunction: splitBlock,
            contentAfter: `<blockquote><p dir="rtl">abc</p></blockquote><p dir="rtl">[]<br></p>`,
        });
    });
    test("should move an empty paragraph after the blockquote with rtl direction if at the end (2)", async () => {
        await testEditor({
            contentBefore: `<blockquote dir="rtl"><p>abc</p><p>[]<br></p></blockquote>`,
            stepFunction: splitBlock,
            contentAfter: `<blockquote dir="rtl"><p>abc</p></blockquote><p dir="rtl">[]<br></p>`,
        });
    });
});
describe("Enter Key", () => {
    test("blockquote should create br on Enter", async () => {
        const { el, editor } = await setupEditor("<p>ab[]</p>");
        expect(getContent(el)).toBe(`<p>ab[]</p>`);

        await insertText(editor, "/");
        await waitFor(".o-we-powerbox");

        await insertText(editor, "quote");
        await press("enter");
        await waitForNone(".o-we-powerbox");
        expect(getContent(el)).toBe("<blockquote>ab[]</blockquote>");

        await insertText(editor, "c");
        await simulateEnter(editor);
        expect(getContent(el)).toBe("<blockquote>abc<br>[]<br></blockquote>");
        await insertText(editor, "d");
        expect(getContent(el)).toBe("<blockquote>abc<br>d[]</blockquote>");
        await insertText(editor, "ef");
        expect(getContent(el)).toBe("<blockquote>abc<br>def[]</blockquote>");
    });
    test("blockquote should create br on Enter (2)", async () => {
        const { el, editor } = await setupEditor("<blockquote>a[]b</blockquote>");
        await simulateEnter(editor);
        expect(getContent(el)).toBe("<blockquote>a<br>[]b</blockquote>");
    });
    test("blockquote should create br on 1st Enter then create p", async () => {
        const { el, editor } = await setupEditor("<blockquote>abc<br>def[]</blockquote>");
        await simulateEnter(editor);
        expect(getContent(el)).toBe("<blockquote>abc<br>def<br>[]<br></blockquote>");
        await simulateEnter(editor);
        expect(getContent(el)).toBe(
            '<blockquote>abc<br>def</blockquote><p o-we-hint-text=\'Type "/" for commands\' class="o-we-hint">[]<br></p>'
        );
    });
});
