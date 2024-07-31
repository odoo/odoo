import { expect, test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";
import { setupEditor } from "../_helpers/editor";
import { insertText } from "../_helpers/user_actions";
import { getContent } from "../_helpers/selection";
import { unformat } from "../_helpers/format";
import { animationFrame } from "@odoo/hoot-mock";

test("typing '1. ' should create number list", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    insertText(editor, "1. ");
    expect(getContent(el)).toBe(`<ol><li placeholder="List" class="o-we-hint">[]<br></li></ol>`);
});

test("typing '1) ' should create number list", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    insertText(editor, "1) ");
    expect(getContent(el)).toBe(`<ol><li placeholder="List" class="o-we-hint">[]<br></li></ol>`);
});

test("Typing '1. ' at the start of existing text should create a numbered list", async () => {
    const { el, editor } = await setupEditor("<p>[]abc</p>");
    insertText(editor, "1) ");
    expect(getContent(el)).toBe(`<ol><li>[]abc</li></ol>`);
});

test("should convert simple number list into bullet list", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    insertText(editor, "1. ");
    insertText(editor, "/bulletedlist");
    press("Enter");
    expect(getContent(el)).toBe(`<ul><li placeholder="List" class="o-we-hint">[]<br></li></ul>`);
});

test("typing 'a. ' should create number list", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    insertText(editor, "a. ");
    expect(getContent(el)).toBe(
        `<ol style="list-style: lower-alpha;"><li placeholder="List" class="o-we-hint">[]<br></li></ol>`
    );
});

test("typing 'a) ' should create number list", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    insertText(editor, "a) ");
    expect(getContent(el)).toBe(
        `<ol style="list-style: lower-alpha;"><li placeholder="List" class="o-we-hint">[]<br></li></ol>`
    );
});

test("should convert lower-alpha list into bullet list", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    insertText(editor, "a. ");
    insertText(editor, "/bulletedlist");
    press("Enter");
    expect(getContent(el)).toBe(
        `<ul style=""><li placeholder="List" class="o-we-hint">[]<br></li></ul>`
    );
});

test("typing 'A. ' should create number list", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    insertText(editor, "A. ");
    expect(getContent(el)).toBe(
        `<ol style="list-style: upper-alpha;"><li placeholder="List" class="o-we-hint">[]<br></li></ol>`
    );
});

test("typing 'A) ' should create number list", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    insertText(editor, "A) ");
    expect(getContent(el)).toBe(
        `<ol style="list-style: upper-alpha;"><li placeholder="List" class="o-we-hint">[]<br></li></ol>`
    );
});

test("should convert upper-alpha list into bullet list", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    insertText(editor, "A. ");
    insertText(editor, "/bulletedlist");
    press("Enter");
    expect(getContent(el)).toBe(
        `<ul style=""><li placeholder="List" class="o-we-hint">[]<br></li></ul>`
    );
});

test("creating list directly inside table column (td)", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    insertText(editor, "/table");
    press("Enter");
    await animationFrame();
    press("Enter");
    press("Backspace");
    insertText(editor, "A. ");
    expect(getContent(el)).toBe(
        unformat(`
            <table class="table table-bordered o_table">
                <tbody>
                    <tr>
                        <td><ol style="list-style: upper-alpha;"><li placeholder="List" class="o-we-hint">[]<br></li></ol></td>
                        <td><p><br></p></td>
                        <td><p><br></p></td>
                    </tr>
                    <tr>
                        <td><p><br></p></td>
                        <td><p><br></p></td>
                        <td><p><br></p></td>
                    </tr>
                    <tr>
                        <td><p><br></p></td>
                        <td><p><br></p></td>
                        <td><p><br></p></td>
                    </tr>
                </tbody>
            </table>
            <p><br></p>`)
    );
});

test("typing '* ' should create bullet list", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    insertText(editor, "* ");
    expect(getContent(el)).toBe(`<ul><li placeholder="List" class="o-we-hint">[]<br></li></ul>`);
});

test("Typing '* ' at the start of existing text should create a bullet list", async () => {
    const { el, editor } = await setupEditor("<p>[]abc</p>");
    insertText(editor, "* ");
    expect(getContent(el)).toBe(`<ul><li>[]abc</li></ul>`);
});

test("typing '- ' should create bullet list", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    insertText(editor, "- ");
    expect(getContent(el)).toBe(`<ul><li placeholder="List" class="o-we-hint">[]<br></li></ul>`);
});

test("should convert a bullet list into a numbered list", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    insertText(editor, "- ");
    insertText(editor, "/numberedlist");
    press("Enter");
    expect(getContent(el)).toBe(`<ol><li placeholder="List" class="o-we-hint">[]<br></li></ol>`);
});

test("typing '[] ' should create checklist and restore the original text when undo", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    insertText(editor, "[] ");
    expect(getContent(el)).toBe(
        `<ul class="o_checklist"><li placeholder="List" class="o-we-hint">[]<br></li></ul>`
    );

    editor.dispatch("HISTORY_UNDO");
    expect(getContent(el)).toBe(`<p>\[\] []</p>`);
});

test("Typing '[] ' at the start of existing text should create a checklist and restore the original text when undo", async () => {
    const { el, editor } = await setupEditor("<p>[]abc</p>");
    insertText(editor, "[] ");
    expect(getContent(el)).toBe(`<ul class="o_checklist"><li>[]abc</li></ul>`);

    editor.dispatch("HISTORY_UNDO");
    expect(getContent(el)).toBe(`<p>\[\] []abc</p>`);
});

test("should convert a checklist into a numbered list", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    insertText(editor, "[] ");
    insertText(editor, "/numberedlist");
    press("Enter");
    expect(getContent(el)).toBe(`<ol><li placeholder="List" class="o-we-hint">[]<br></li></ol>`);
});

test("List should not be created when typing '1. ' at the end the text", async () => {
    const { el, editor } = await setupEditor("<p>abc[]</p>");
    insertText(editor, "1. ");
    expect(getContent(el)).toBe(`<p>abc1. []</p>`);
});

test("List should not be created when typing '1. ' between the existing text", async () => {
    const { el, editor } = await setupEditor("<p>a[]bc</p>");
    insertText(editor, "1. ");
    expect(getContent(el)).toBe(`<p>a1. []bc</p>`);
});
