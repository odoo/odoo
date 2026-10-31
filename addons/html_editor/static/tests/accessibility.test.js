import { Plugin } from "@html_editor/plugin";
import { describe, expect, test } from "@odoo/hoot";
import { click, press, queryAllTexts, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { contains } from "@web/../tests/web_test_helpers";
import { setupEditor } from "./_helpers/editor";
import { insertText } from "./_helpers/user_actions";
import { execCommand } from "./_helpers/userCommands";

class AccessibilityTestPlugin extends Plugin {
    static id = "accessibilityTest";
    resources = {
        user_commands: [
            { id: "commandA", run: () => {}, isAvailable: () => true },
            { id: "unlabelledCommand", run: () => {} },
            { id: "commandB", run: () => {}, isAvailable: () => false },
        ],
        shortcuts: [
            {
                label: "Test command A",
                category: "Test shortcuts A",
                hotkey: "f6",
                commandId: "commandA",
            },
            {
                category: "Unlabelled test shortcuts",
                hotkey: "f7",
                commandId: "unlabelledCommand",
            },
            {
                label: "Test command B",
                category: "Test shortcuts B",
                hotkey: "f8",
                commandId: "commandB",
            },
        ],
        shorthands: [
            {
                label: "Test shorthand A",
                literals: [":test-a", ":a"],
                commandId: "commandA",
            },
            { literals: [":unlabelled"], commandId: "unlabelledCommand" },
            {
                label: "Test shorthand B",
                literals: [":test-b"],
                commandId: "commandB",
            },
        ],
    };
}

async function openAccessibilityDialog(config = {}) {
    const result = await setupEditor("<p>a[]</p>", {
        config: { accessibilityDialog: true, ...config },
    });
    execCommand(result.editor, "accessibility");
    await waitFor('.modal-title:contains("Accessibility help")');
    return result;
}

describe("Accessibility help", () => {
    test("Ctrl+K lists accessibility help and opens it on click", async () => {
        const { el } = await setupEditor("<p>a[]</p>", {
            config: { accessibilityDialog: true },
        });
        await press(["ctrl", "k"]);
        await animationFrame();
        await contains(".o_command_palette_search input").fill("Editor accessibility", {
            confirm: false,
        });
        await animationFrame();
        await waitFor('.o_command_name:contains("Editor accessibility")');
        expect(".o_command").toHaveCount(1);
        expect(".o_command_name").toHaveText("Editor accessibility");

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
        await openAccessibilityDialog();
        expect('.modal-body h4:contains("Content editing keystrokes")').toHaveCount(1);
        expect('.modal-body h5:contains("Text formatting")').toHaveCount(1);
        expect('.modal-body tr:has(th:contains("Bold")) kbd:last').toHaveText("B");
        expect('.modal-body h5:contains("Shorthands")').toHaveCount(1);
        expect('.modal-body tr:has(th:contains("Heading 3")) code').toHaveText("###");
        expect('.modal-body tr:has(th:contains("Heading 3")) kbd').toHaveText("Space");
    });

    test("only displays labelled shortcuts and shorthands", async () => {
        await openAccessibilityDialog({ includePlugins: [AccessibilityTestPlugin] });
        expect('.modal-body th:contains("Test command A")').toHaveCount(1);
        expect('.modal-body th:contains("Test shorthand A")').toHaveCount(1);
        expect('.modal-body kbd:contains("F6")').toHaveCount(1);
        expect('.modal-body kbd:contains("F7")').toHaveCount(0);
        expect('.modal-body h5:contains("Unlabelled test shortcuts")').toHaveCount(0);
        expect('.modal-body code:contains(":unlabelled")').toHaveCount(0);
        expect(queryAllTexts('.modal-body tr:has(th:contains("Test shorthand A")) code')).toEqual([
            ":test-a",
            ":a",
        ]);
    });

    test("filters out shortcuts and shorthands whose commands are unavailable", async () => {
        await openAccessibilityDialog({ includePlugins: [AccessibilityTestPlugin] });
        expect('.modal-body th:contains("Test command A")').toHaveCount(1);
        expect('.modal-body th:contains("Test shorthand A")').toHaveCount(1);
        expect('.modal-body th:contains("Test command B")').toHaveCount(0);
        expect('.modal-body th:contains("Test shorthand B")').toHaveCount(0);
        expect('.modal-body h5:contains("Test shortcuts B")').toHaveCount(0);
        expect('.modal-body kbd:contains("F8")').toHaveCount(0);
        expect('.modal-body code:contains(":test-b")').toHaveCount(0);
    });

    test("hides accessibility commands when accessibility help is disabled", async () => {
        const { editor } = await setupEditor("<p>a[]</p>", {
            config: { accessibilityDialog: false },
        });
        await press(["ctrl", "k"]);
        await contains(".o_command_palette_search input").fill("Editor accessibility", {
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

    test("hides accessibility commands by default", async () => {
        const { editor } = await setupEditor("<p>a[]</p>");
        await press(["ctrl", "k"]);
        await contains(".o_command_palette_search input").fill("Editor accessibility", {
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
