import { describe, expect, test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";
import { setupEditor, testEditor } from "./_helpers/editor";
import { undo } from "./_helpers/user_actions";

function cut(editor) {
    const clipboardData = new DataTransfer();
    const cutEvent = new ClipboardEvent("cut", { clipboardData });
    editor.editable.dispatchEvent(cutEvent);
    return clipboardData;
}

describe("range collapsed", () => {
    test("should ignore cutting an empty selection with empty clipboardData", async () => {
        const { editor } = await setupEditor("<p>[]</p>");
        const clipboardData = cut(editor);
        // Check that nothing was set as clipboard content
        expect(clipboardData.types.length).toBe(0);
    });

    test("should ignore cutting an empty selection with clipboardData", async () => {
        const { editor } = await setupEditor("<p>[]</p>");
        const clipboardData = new DataTransfer();
        clipboardData.setData("text/plain", "should stay");
        const cutEvent = new ClipboardEvent("cut", { clipboardData });
        editor.editable.dispatchEvent(cutEvent);
        // Check that clipboard data was not overwritten
        expect(clipboardData.getData("text/plain")).toBe("should stay");
    });
});

describe("range not collapsed", () => {
    test("should cut a selection as text/plain, text/html and application/vnd.odoo.odoo-editor", async () => {
        await testEditor({
            contentBefore: "<p>a[bcd]e</p>",
            stepFunction: async (editor) => {
                const clipboardData = cut(editor);
                expect(clipboardData.getData("text/plain")).toBe("bcd");
                expect(clipboardData.getData("text/html")).toBe("<p>bcd</p>");
                expect(clipboardData.getData("application/vnd.odoo.odoo-editor")).toBe(
                    "<p>bcd</p>"
                );
            },
            contentAfter: "<p>a[]e</p>",
        });
        await testEditor({
            contentBefore: "<p>[abc<br>efg]</p>",
            stepFunction: async (editor) => {
                const clipboardData = cut(editor);
                expect(clipboardData.getData("text/plain")).toBe("abc\nefg");
                expect(clipboardData.getData("text/html")).toBe("<p>abc<br>efg</p>");
                expect(clipboardData.getData("application/vnd.odoo.odoo-editor")).toBe(
                    "<p>abc<br>efg</p>"
                );
            },
            contentAfter: "<p>[]<br></p>",
        });
    });

    test("should cut selection and register it as a history step", async () => {
        await testEditor({
            contentBefore: "<p>a[bcd]e</p>",
            stepFunction: async (editor) => {
                const history = editor.plugins.find((p) => p.constructor.id === "history");
                const historyStepsCount = history.steps.length;
                cut(editor);
                expect(history.steps.length).toBe(historyStepsCount + 1);
                undo(editor);
            },
            contentAfter: "<p>a[bcd]e</p>",
        });
    });

    test("should not restore cut content when cut followed by delete forward", async () => {
        await testEditor({
            contentBefore: "<p>a[]bcde</p>",
            stepFunction: async (editor) => {
                // Set selection to a[bcd]e.
                const selection = editor.document.getSelection();
                selection.extend(selection.anchorNode, 4);
                cut(editor);
                await press("Delete");
            },
            contentAfter: "<p>a[]</p>",
        });
    });
});
