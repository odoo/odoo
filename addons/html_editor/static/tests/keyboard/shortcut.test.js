import { Plugin } from "@html_editor/plugin";
import { expect, test } from "@odoo/hoot";
import { setupEditor } from "../_helpers/editor";
import { press } from "@odoo/hoot-dom";
import { insertSpace, insertText } from "../_helpers/user_actions";
import { ShortCutPlugin } from "@html_editor/core/shortcut_plugin";

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
        config: { includePlugins: [TestPlugin] },
    });

    expect(count).toBe(0);
    await press("a");
    expect(count).toBe(1);
    await press("b");
    expect(count).toBe(1);
});

test("shortcut should not remove empty line and should be inline", async () => {
    const { el, editor } = await setupEditor("<div>a<br><br>b[]</div>", {
        config: { includePlugins: [ShortCutPlugin] },
    });
    await insertText(editor, "->");
    await insertSpace(editor);
    expect(el.innerHTML).toBe(`<div class="o-paragraph">a<br><br>b→&nbsp;</div>`);
});

test("shortcut should keep two empty lines and add create a list block", async () => {
    const { el, editor } = await setupEditor(`<div class="o-paragraph">a<br><br><br>[]</div>`, {
        config: { includePlugins: [ShortCutPlugin] },
    });
    await insertText(editor, "1.");
    await insertSpace(editor);
    expect(el.innerHTML).toBe(
        `<div class="o-paragraph">a<br><br><br></div><ol><li o-we-hint-text="List" class="o-we-hint"><br></li></ol>`
    );
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
        config: { includePlugins: [TestPlugin] },
        props: { iframe: true },
    });

    expect(count).toBe(0);
    await press("a");
    expect(count).toBe(1);
    await press("b");
    expect(count).toBe(1);
});
