import { expect, test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";
import { setupEditor } from "../_helpers/editor";
import { insertText } from "../_helpers/user_actions";
import { getContent } from "../_helpers/selection";
import { unformat } from "../_helpers/format";
import { animationFrame } from "@odoo/hoot-mock";
import { execCommand } from "../_helpers/userCommands";

test("typing '1. ' should create number list", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    await insertText(editor, "1. ");
    expect(getContent(el)).toBe(`<ol><li o-we-hint-text="List" class="o-we-hint">[]<br></li></ol>`);
});

test("typing '1) ' should create number list", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    await insertText(editor, "1) ");
    expect(getContent(el)).toBe(`<ol><li o-we-hint-text="List" class="o-we-hint">[]<br></li></ol>`);
});

test("Typing '1. ' at the start of existing text should create a numbered list", async () => {
    const { el, editor } = await setupEditor("<p>[]abc</p>");
    await insertText(editor, "1) ");
    expect(getContent(el)).toBe(`<ol><li>[]abc</li></ol>`);
});

test("typing '1. ' should keep cursor inside formatting element when creating a list", async () => {
    const { el, editor } = await setupEditor("<p><strong><u>[]</u></strong></p>");
    await insertText(editor, "1. ");
    expect(getContent(el)).toBe(
        unformat(
            `<ol>
                <li o-we-hint-text="List" class="o-we-hint">
                    <strong><u data-oe-zws-empty-inline="">[]\u200b</u></strong>
                </li>
            </ol>`
        )
    );
});

test("should convert simple number list into bullet list", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    await insertText(editor, "1. ");
    await insertText(editor, "/bulletedlist");
    await press("Enter");
    expect(getContent(el)).toBe(`<ul><li o-we-hint-text="List" class="o-we-hint">[]<br></li></ul>`);
});

test("typing 'a. ' should create number list", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    await insertText(editor, "a. ");
    expect(getContent(el)).toBe(
        `<ol style="list-style: lower-alpha;"><li o-we-hint-text="List" class="o-we-hint">[]<br></li></ol>`
    );
});

test("typing 'a) ' should create number list", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    await insertText(editor, "a) ");
    expect(getContent(el)).toBe(
        `<ol style="list-style: lower-alpha;"><li o-we-hint-text="List" class="o-we-hint">[]<br></li></ol>`
    );
});

test("should convert lower-alpha list into bullet list", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    await insertText(editor, "a. ");
    await insertText(editor, "/bulletedlist");
    await press("Enter");
    expect(getContent(el)).toBe(
        `<ul style=""><li o-we-hint-text="List" class="o-we-hint">[]<br></li></ul>`
    );
});

test("typing 'A. ' should create number list", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    await insertText(editor, "A. ");
    expect(getContent(el)).toBe(
        `<ol style="list-style: upper-alpha;"><li o-we-hint-text="List" class="o-we-hint">[]<br></li></ol>`
    );
});

test("typing 'A) ' should create number list", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    await insertText(editor, "A) ");
    expect(getContent(el)).toBe(
        `<ol style="list-style: upper-alpha;"><li o-we-hint-text="List" class="o-we-hint">[]<br></li></ol>`
    );
});

test("should convert upper-alpha list into bullet list", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    await insertText(editor, "A. ");
    await insertText(editor, "/bulletedlist");
    await press("Enter");
    expect(getContent(el)).toBe(
        `<ul style=""><li o-we-hint-text="List" class="o-we-hint">[]<br></li></ul>`
    );
});

test("creating list directly inside table column (td)", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    await insertText(editor, "/table");
    await press("Enter");
    await animationFrame();
    await press("Enter");
    await press("Backspace");
    await insertText(editor, "A. ");
    expect(getContent(el)).toBe(
        unformat(`
            <p data-selection-placeholder=""><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr>
                        <td><ol style="list-style: upper-alpha;"><li o-we-hint-text="List" class="o-we-hint">[]<br></li></ol></td>
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
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
    );
});

test("typing '* ' should create bullet list", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    await insertText(editor, "* ");
    expect(getContent(el)).toBe(`<ul><li o-we-hint-text="List" class="o-we-hint">[]<br></li></ul>`);
});

test("Typing '* ' at the start of existing text should create a bullet list", async () => {
    const { el, editor } = await setupEditor("<p>[]abc</p>");
    await insertText(editor, "* ");
    expect(getContent(el)).toBe(`<ul><li>[]abc</li></ul>`);
});

test("typing '- ' should create bullet list", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    await insertText(editor, "- ");
    expect(getContent(el)).toBe(`<ul><li o-we-hint-text="List" class="o-we-hint">[]<br></li></ul>`);
});

test("should convert a bullet list into a numbered list", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    await insertText(editor, "- ");
    await insertText(editor, "/numberedlist");
    await press("Enter");
    expect(getContent(el)).toBe(`<ol><li o-we-hint-text="List" class="o-we-hint">[]<br></li></ol>`);
});

test("typing '[] ' should create checklist and restore the original text when undo", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    await insertText(editor, "[] ");
    expect(getContent(el)).toBe(
        `<ul class="o_checklist"><li o-we-hint-text="List" class="o-we-hint">[]<br></li></ul>`
    );

    execCommand(editor, "historyUndo");
    expect(getContent(el)).toBe(`<p>[] []</p>`);
});

test("Typing '[] ' at the start of existing text should create a checklist and restore the original text when undo", async () => {
    const { el, editor } = await setupEditor("<p>[]abc</p>");
    await insertText(editor, "[] ");
    expect(getContent(el)).toBe(`<ul class="o_checklist"><li>[]abc</li></ul>`);

    execCommand(editor, "historyUndo");
    expect(getContent(el)).toBe(`<p>[] []abc</p>`);
});

test("should convert a checklist into a numbered list", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    await insertText(editor, "[] ");
    await insertText(editor, "/numberedlist");
    await press("Enter");
    expect(getContent(el)).toBe(`<ol><li o-we-hint-text="List" class="o-we-hint">[]<br></li></ol>`);
});

test("List should not be created when typing '1. ' at the end the text", async () => {
    const { el, editor } = await setupEditor("<p>abc[]</p>");
    await insertText(editor, "1. ");
    expect(getContent(el)).toBe(`<p>abc1. []</p>`);
});

test("List should not be created when typing '1. ' between the existing text", async () => {
    const { el, editor } = await setupEditor("<p>a[]bc</p>");
    await insertText(editor, "1. ");
    expect(getContent(el)).toBe(`<p>a1. []bc</p>`);
});

test("typing space inside formated text with a '*' at the starting of text should not transform to list", async () => {
    const { el, editor } = await setupEditor("<p>* a<strong>b[]cd</strong>e</p>");
    await insertText(editor, " ");
    expect(getContent(el)).toBe(`<p>* a<strong>b []cd</strong>e</p>`);
});
