import { describe, expect, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "../_helpers/editor";
import { getContent } from "../_helpers/selection";
import { execCommand } from "../_helpers/userCommands";
import { simulateArrowKeyPress } from "../_helpers/user_actions";
import { animationFrame } from "@odoo/hoot-dom";

async function insertSeparator(editor) {
    execCommand(editor, "insertSeparator");
}

describe("insert separator", () => {
    test("should insert a separator inside editable with contenteditable set to false", async () => {
        await testEditor({
            contentBefore: "<p>[]<br></p>",
            stepFunction: insertSeparator,
            contentAfterEdit: `<p data-selection-placeholder="" style="margin: 8px 0px -9px;"><br></p><hr contenteditable="false"><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`,
            contentAfter: "<hr><p>[]<br></p>",
        });
    });

    test("should insert a separator inside editable with contenteditable set to false before the block", async () => {
        await testEditor({
            contentBefore: "<p>[]abc<br></p>",
            stepFunction: insertSeparator,
            contentAfterEdit: `<p data-selection-placeholder="" style="margin: 8px 0px -9px;"><br></p><hr contenteditable="false"><p>[]abc<br></p>`,
            contentAfter: "<hr><p>[]abc<br></p>",
        });
    });

    test("should insert a separator before current element if empty", async () => {
        await testEditor({
            contentBefore: "<p>content</p><p>[]<br></p>",
            stepFunction: insertSeparator,
            contentAfterEdit: `<p>content</p><hr contenteditable="false"><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`,
            contentAfter: "<p>content</p><hr><p>[]<br></p>",
        });
    });

    test("should insert a separator after current element if it contains text", async () => {
        await testEditor({
            contentBefore: "<p>content</p><p>text[]</p>",
            stepFunction: insertSeparator,
            contentAfterEdit: `<p>content</p><p>text</p><hr contenteditable="false"><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`,
            contentAfter: "<p>content</p><p>text</p><hr><p>[]<br></p>",
        });
    });

    test("should insert a separator before current empty paragraph related element but remain inside the div", async () => {
        await testEditor({
            contentBefore: "<div><p>[]<br></p></div>",
            stepFunction: insertSeparator,
            contentAfter: "<div><hr><p>[]<br></p></div>",
        });
    });

    test("should insert a separator after current paragraph related element containing text but remain inside the div", async () => {
        await testEditor({
            contentBefore: "<div><p>content[]</p></div>",
            stepFunction: insertSeparator,
            contentAfter: "<div><p>content</p><hr><p>[]<br></p></div>",
        });
    });

    test("should not insert a separator inside a list", async () => {
        await testEditor({
            contentBefore: "<ul><li>[]<br></li></ul>",
            stepFunction: insertSeparator,
            contentAfter: "<ul><li>[]<br></li></ul>",
        });
    });

    test("should insert a separator before a empty p element inside a table cell", async () => {
        await testEditor({
            contentBefore: "<table><tbody><tr><td><p>[]<br></p></td></tr></tbody></table>",
            stepFunction: insertSeparator,
            contentAfter: "<table><tbody><tr><td><hr><p>[]<br></p></td></tr></tbody></table>",
        });
    });

    test("should insert a separator after a p element containing text inside a table cell", async () => {
        await testEditor({
            contentBefore: "<table><tbody><tr><td><p>content[]</p></td></tr></tbody></table>",
            stepFunction: insertSeparator,
            contentAfter:
                "<table><tbody><tr><td><p>content</p><hr><p>[]<br></p></td></tr></tbody></table>",
        });
    });

    test("should insert a seperator before a empty block node", async () => {
        await testEditor({
            contentBefore: "<div>[]<br></div>",
            stepFunction: insertSeparator,
            contentAfter: "<hr><div>[]<br></div>",
        });
    });

    test("should insert a seperator after a block node containing text", async () => {
        await testEditor({
            contentBefore: "<div>content[]</div>",
            stepFunction: insertSeparator,
            contentAfter: "<div>content</div><hr><p>[]<br></p>",
        });
    });

    test("should set the contenteditable attribute to false on the separator when inserted as a child after normalization", async () => {
        const { el, editor } = await setupEditor("<p>[]<br></p>");
        const div = editor.document.createElement("div");
        const separator = editor.document.createElement("hr");
        div.append(separator);
        el.append(div);
        editor.shared.history.addStep();
        expect(getContent(el)).toBe(
            `<p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p><div><hr contenteditable="false"></div><p data-selection-placeholder=""><br></p>`
        );
    });

    test("should apply custom selection on separator when selected", async () => {
        const { el, editor } = await setupEditor("<p>abc</p><p>x[]yz</p>");
        await insertSeparator(editor);
        expect(getContent(el)).toBe(
            `<p>abc</p><p>xyz</p><hr contenteditable="false"><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`
        );

        simulateArrowKeyPress(editor, ["Shift", "ArrowUp"]);
        await animationFrame();

        expect(getContent(el)).toBe(
            `<p>abc</p><p>]xyz</p><hr contenteditable="false" class="o_selected_hr"><p>[<br></p>`
        );
    });

    test("should remove custom selection on separator when not selected", async () => {
        const { el, editor } = await setupEditor(
            '<p>[abc</p><hr contenteditable="false"><p>xyz]</p>'
        );
        expect(getContent(el)).toBe(
            `<p>[abc</p><hr contenteditable="false" class="o_selected_hr"><p>xyz]</p>`
        );

        simulateArrowKeyPress(editor, ["Shift", "ArrowUp"]);
        await animationFrame();

        expect(getContent(el)).toBe(`<p>[abc]</p><hr contenteditable="false"><p>xyz</p>`);
    });
});
