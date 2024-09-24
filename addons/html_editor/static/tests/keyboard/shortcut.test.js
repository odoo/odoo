import { Plugin } from "@html_editor/plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { expect, test } from "@odoo/hoot";
import { setupEditor } from "../_helpers/editor";
import { press } from "@odoo/hoot-dom";

test("shortcut plugin allow registering shortcuts", async () => {
    let count = 0;
    class TestPlugin extends Plugin {
        static name = "test";
        resources = {
            shortcuts: [{ hotkey: "a", command: "TEST_CMD" }],
        };
        handleCommand(command, payload) {
            if (command === "TEST_CMD") {
                count++;
            }
        }
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

test.tags("iframe")("shortcut plugin allow registering shortcuts in iframe", async () => {
    let count = 0;
    class TestPlugin extends Plugin {
        static name = "test";
        resources = {
            shortcuts: [{ hotkey: "a", command: "TEST_CMD" }],
        };
        handleCommand(command, payload) {
            if (command === "TEST_CMD") {
                count++;
            }
        }
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
