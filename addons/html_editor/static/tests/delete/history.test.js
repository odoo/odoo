import { describe, expect, test } from "@odoo/hoot";
import { setupEditor } from "../_helpers/editor";
import { press } from "@odoo/hoot-dom";
import { getContent } from "../_helpers/selection";

describe("delete backward", () => {
    test("should register a history step (collapsed selection)", async () => {
        const { el, editor } = await setupEditor("<p>ab[]cd</p>");

        await press("Backspace");
        expect(getContent(el)).toBe("<p>a[]cd</p>");

        editor.dispatch("HISTORY_UNDO");
        expect(getContent(el)).toBe("<p>ab[]cd</p>");

        editor.dispatch("HISTORY_REDO");
        expect(getContent(el)).toBe("<p>a[]cd</p>");
    });

    test("should register a history step (non-collapsed selection)", async () => {
        const { el, editor } = await setupEditor("<p>ab[cd]ef</p>");

        await press("Backspace");
        expect(getContent(el)).toBe("<p>ab[]ef</p>");

        editor.dispatch("HISTORY_UNDO");
        expect(getContent(el)).toBe("<p>ab[cd]ef</p>");

        editor.dispatch("HISTORY_REDO");
        expect(getContent(el)).toBe("<p>ab[]ef</p>");
    });
});

describe("delete forward", () => {
    test("should register a history step (collapsed selection)", async () => {
        const { el, editor } = await setupEditor("<p>ab[]cd</p>");

        await press("Delete");
        expect(getContent(el)).toBe("<p>ab[]d</p>");

        editor.dispatch("HISTORY_UNDO");
        expect(getContent(el)).toBe("<p>ab[]cd</p>");

        editor.dispatch("HISTORY_REDO");
        expect(getContent(el)).toBe("<p>ab[]d</p>");
    });

    test("should register a history step (non-collapsed selection)", async () => {
        const { el, editor } = await setupEditor("<p>ab[cd]ef</p>");

        await press("Delete");
        expect(getContent(el)).toBe("<p>ab[]ef</p>");

        editor.dispatch("HISTORY_UNDO");
        expect(getContent(el)).toBe("<p>ab[cd]ef</p>");

        editor.dispatch("HISTORY_REDO");
        expect(getContent(el)).toBe("<p>ab[]ef</p>");
    });
});
