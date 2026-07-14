import { Plugin } from "@html_editor/plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { expect, test } from "@odoo/hoot";
import { setupEditor } from "../_helpers/editor";
import { press } from "@odoo/hoot-dom";

test("shortcut plugin allow registering shortcuts", async () => {
    let count = 0;
    class TestPlugin extends Plugin {
        static id = "test";
        resources = {
            user_commands: [{ id: "TEST_CMD", run: () => count++ }],
            shortcuts: [{ hotkey: "a", commandId: "TEST_CMD" }],
        };
    }
    await setupEditor(`<p>test[]</p>`, {
        config: { Plugins: [...MAIN_PLUGINS, TestPlugin] },
    });

    expect(count).toBe(0);
    await press("a");
    expect(count).toBe(1);
    await press("b");
    expect(count).toBe(1);
});

test.tags("iframe");
test("shortcut plugin allow registering shortcuts in iframe", async () => {
    let count = 0;
    class TestPlugin extends Plugin {
        static id = "test";
        resources = {
            user_commands: [{ id: "TEST_CMD", run: () => count++ }],
            shortcuts: [{ hotkey: "a", commandId: "TEST_CMD" }],
        };
    }
    await setupEditor(`<p>test[]</p>`, {
        config: { Plugins: [...MAIN_PLUGINS, TestPlugin] },
        props: { iframe: true },
    });

    expect(count).toBe(0);
    await press("a");
    expect(count).toBe(1);
    await press("b");
    expect(count).toBe(1);
});
