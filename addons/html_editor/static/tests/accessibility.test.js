import { AccessibilityPlugin } from "@html_editor/main/accessibility/accessibility_plugin";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { describe, expect, test } from "@odoo/hoot";
import { click, press, queryAllTexts, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { contains } from "@web/../tests/web_test_helpers";
import { setupEditor } from "./_helpers/editor";
import { insertText } from "./_helpers/user_actions";

class AccessibilityTestPlugin extends Plugin {
    static id = "accessibilityTest";
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            { id: "commandA", title: "Test command A", run: () => {} },
            { id: "uncategorizedCommand", title: "Uncategorized command", run: () => {} },
        ],
        shortcut_categories: [withSequence(1, { id: "testA", name: "Test shortcuts A" })],
        shortcuts: [
            {
                categoryId: "testA",
                hotkey: "f6",
                commandId: "commandA",
            },
            { hotkey: "f7", commandId: "uncategorizedCommand" },
        ],
        shorthands: [
            {
                title: "Test shorthand A",
                literals: [":test-a", ":a"],
                commandId: "commandA",
            },
            { literals: [":default-title"], commandId: "commandA" },
        ],
    };
}

describe("Accessibility help", () => {
    test("Ctrl+K lists accessibility help and opens it on click", async () => {
        const { el } = await setupEditor("<p>a[]</p>", {
            config: { includePlugins: [AccessibilityPlugin] },
        });
        await press(["ctrl", "k"]);
        await animationFrame();
        await contains(".o_command_palette_search input").fill("Accessibility help", {
            confirm: false,
        });
        await animationFrame();
        await waitFor('.o_command_name:contains("Accessibility help")');
        expect(".o_command").toHaveCount(1);
        expect(".o_command_name").toHaveText("Accessibility help");

        await click(".o_command");
        await waitFor('.modal-title:contains("Accessibility help")');
        await animationFrame();
        expect(".o_command_palette").toHaveCount(0);
        expect(".modal-footer button").toHaveText("Close");
        expect(".modal-footer button").toBeFocused();

        await contains(".modal-footer button").click();
        expect(".modal").toHaveCount(0);
        expect(el).toBeFocused();
    });

    test("displays editor commands, their shortcuts, and shorthand literals", async () => {
        const { editor } = await setupEditor("<p>a[]</p>", {
            config: { includePlugins: [AccessibilityPlugin] },
        });
        await insertText(editor, "/Accessibility");
        await animationFrame();
        await click('.o-we-command-name:contains("Accessibility help")');
        await waitFor('.modal-title:contains("Accessibility help")');
        expect('.modal-body h4:contains("Content editing keystrokes")').toHaveCount(1);
        expect('.modal-body h5:contains("Text formatting")').toHaveCount(1);
        expect('.modal-body tr:has(th:contains("Bold")) kbd:last').toHaveText("B");
        expect('.modal-body h4:contains("Shorthands")').toHaveCount(1);
        expect('.modal-body tr:has(th:contains("Heading 3")) code').toHaveText("###");
    });

    test("only displays shortcuts with a registered category", async () => {
        const { editor } = await setupEditor("<p>a[]</p>", {
            config: { includePlugins: [AccessibilityPlugin, AccessibilityTestPlugin] },
        });
        await insertText(editor, "/Accessibility");
        await animationFrame();
        await click('.o-we-command-name:contains("Accessibility help")');
        await waitFor('.modal-title:contains("Accessibility help")');
        expect('.modal-body th:contains("Test command A")').toHaveCount(2);
        expect('.modal-body th:contains("Test shorthand A")').toHaveCount(1);
        expect('.modal-body kbd:contains("F6")').toHaveCount(1);
        expect('.modal-body kbd:contains("F7")').toHaveCount(0);
        expect('.modal-body th:contains("Uncategorized command")').toHaveCount(0);
        expect(queryAllTexts('.modal-body tr:has(th:contains("Test shorthand A")) code')).toEqual([
            ":test-a",
            ":a",
        ]);
    });

    test("omits checklist shortcuts and shorthands when checklists are disabled", async () => {
        const { editor } = await setupEditor("<p>a[]</p>", {
            config: { includePlugins: [AccessibilityPlugin], allowChecklist: false },
        });
        await insertText(editor, "/Accessibility");
        await animationFrame();
        await click('.o-we-command-name:contains("Accessibility help")');
        await waitFor('.modal-title:contains("Accessibility help")');
        expect('.modal-body th:contains("Checklist")').toHaveCount(0);
    });

    test("hides accessibility commands by default", async () => {
        const { editor } = await setupEditor("<p>a[]</p>");
        await press(["ctrl", "k"]);
        await contains(".o_command_palette_search input").fill("Accessibility help", {
            confirm: false,
        });
        expect(".o_command").toHaveCount(0);
        await press("Escape");
        await animationFrame();

        await insertText(editor, "/accessibility");
        await animationFrame();
        expect('.o-we-command-name:contains("Accessibility help")').toHaveCount(0);
        expect('.modal-title:contains("Accessibility help")').toHaveCount(0);
    });
});
