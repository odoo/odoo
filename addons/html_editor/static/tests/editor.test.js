import { Plugin } from "@html_editor/plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { expect, test } from "@odoo/hoot";
import { setupEditor } from "./_helpers/editor";
import { insertText } from "./_helpers/user_actions";
import { getContent } from "./_helpers/selection";

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
    await insertText(editor, "a");

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

test("CLEAN_FOR_SAVE is done last", async () => {
    // This test uses custom elements tag `c-div` to make sure they won't fall into
    // a case where they won't be merged anyway.
    // Without the proper fix, this test fails with sibling elements `c-div` merged together
    class TestPlugin extends Plugin {
        setup() {
            for (const el of this.editable.querySelectorAll("c-div")) {
                el.classList.add("oe_unbreakable");
            }
        }
        handleCommand(cmd, payload) {
            if (cmd === "CLEAN_FOR_SAVE") {
                for (const el of payload.root.querySelectorAll("c-div")) {
                    el.removeAttribute("class");
                }
            }
        }
    }
    const Plugins = [...MAIN_PLUGINS, TestPlugin];
    const { editor } = await setupEditor(`<div><c-div>a</c-div><c-div>b</c-div></div>`, {
        config: { Plugins },
    });

    const el = editor.getElContent();
    expect(getContent(el)).toBe(`<div><c-div>a</c-div><c-div>b</c-div></div>`);
});
