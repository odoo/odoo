import { Plugin } from "@html_editor/plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { expect, test } from "@odoo/hoot";
import { setupEditor } from "./_helpers/editor";
import { insertText } from "./_helpers/user_actions";

test("can get content of an Editor", async () => {
    const { el, editor } = await setupEditor("<p>hel[lo] world</p>", {});
    expect(el.innerHTML).toBe(`<p>hello world</p>`);
    expect(editor.getContent()).toBe(`<p>hello world</p>`);
});

test("can get content of an empty paragraph", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>", {});
    expect(el.innerHTML).toBe(
        `<p placeholder="Type &quot;/&quot; for commands" class="o-we-hint"></p>`
    );
    expect(editor.getContent()).toBe(`<p></p>`);
});

test("is notified when content is changed", async () => {
    let n = 0;
    const { editor } = await setupEditor("<p>hello[] world</p>", {
        config: { onChange: () => n++ },
    });
    expect(n).toBe(0);
    insertText(editor, "a");

    expect(editor.getContent()).toBe(`<p>helloa world</p>`);
    expect(n).toBe(1);
});

test("plugin destruction is reverse of instantiation order", async () => {
    function makeTestPlugin(name, dependencies = []) {
        return class TestPlugin extends Plugin {
            static name = name;
            static dependencies = dependencies;

            setup() {
                expect.step(`setup: ${name}`);
            }
            destroy() {
                expect.step(`destroy: ${name}`);
            }
        };
    }
    const Plugins = [...MAIN_PLUGINS, makeTestPlugin("first"), makeTestPlugin("second", ["first"])];
    const { editor } = await setupEditor(`<p>[]</p>`, { config: { Plugins } });
    expect.verifySteps(["setup: first", "setup: second"]);
    editor.destroy();
    expect.verifySteps(["destroy: second", "destroy: first"]);
});

test("Remove odoo-editor-editable class after every plugin is destroyed", async () => {
    class TestPlugin extends Plugin {
        static name = "test";
        destroy() {
            const p = this.editable.querySelector("p");
            if (closestElement(p, "div")) {
                expect.step("operation");
            }
        }
    }
    const Plugins = [...MAIN_PLUGINS, TestPlugin];
    const { editor } = await setupEditor(`<div><p>a</p></div>`, { config: { Plugins } });
    editor.destroy();
    expect.verifySteps(["operation"]);
});
