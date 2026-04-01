import { describe, expect, test } from "@odoo/hoot";
import { setupEditor } from "../_helpers/editor";
import { press } from "@odoo/hoot-dom";
import { getContent } from "../_helpers/selection";
import { execCommand } from "../_helpers/userCommands";

describe("delete backward", () => {
    test("should register a history step (collapsed selection)", async () => {
        const { el, editor } = await setupEditor("<p>ab[]cd</p>");

        await press("Backspace");
        expect(getContent(el)).toBe("<p>a[]cd</p>");

        execCommand(editor, "historyUndo");
        expect(getContent(el)).toBe("<p>ab[]cd</p>");

        execCommand(editor, "historyRedo");
        expect(getContent(el)).toBe("<p>a[]cd</p>");
    });

    test("should register a history step (non-collapsed selection)", async () => {
        const { el, editor } = await setupEditor("<p>ab[cd]ef</p>");

        await press("Backspace");
        expect(getContent(el)).toBe("<p>ab[]ef</p>");

        execCommand(editor, "historyUndo");
        expect(getContent(el)).toBe("<p>ab[cd]ef</p>");

        execCommand(editor, "historyRedo");
        expect(getContent(el)).toBe("<p>ab[]ef</p>");
    });
});

describe("delete forward", () => {
    test("should register a history step (collapsed selection)", async () => {
        const { el, editor } = await setupEditor("<p>ab[]cd</p>");

        await press("Delete");
        expect(getContent(el)).toBe("<p>ab[]d</p>");

        execCommand(editor, "historyUndo");
        expect(getContent(el)).toBe("<p>ab[]cd</p>");

        execCommand(editor, "historyRedo");
        expect(getContent(el)).toBe("<p>ab[]d</p>");
    });

    test("should register a history step (non-collapsed selection)", async () => {
        const { el, editor } = await setupEditor("<p>ab[cd]ef</p>");

        await press("Delete");
        expect(getContent(el)).toBe("<p>ab[]ef</p>");

        execCommand(editor, "historyUndo");
        expect(getContent(el)).toBe("<p>ab[cd]ef</p>");

        execCommand(editor, "historyRedo");
        expect(getContent(el)).toBe("<p>ab[]ef</p>");
    });
});
