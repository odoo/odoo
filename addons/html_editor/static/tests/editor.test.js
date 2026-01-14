import { Editor } from "@html_editor/editor";
import { Plugin } from "@html_editor/plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { beforeEach, expect, test } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupEditor, testEditor } from "./_helpers/editor";
import { insertText } from "./_helpers/user_actions";
import { getContent } from "./_helpers/selection";
import { unformat } from "./_helpers/format";

beforeEach(() => {
    patchWithCleanup(Editor.prototype, {
        preparePlugins() {
            this.config.Plugins = (this.config.Plugins || MAIN_PLUGINS).filter(
                (plugin) => plugin.id !== "editorVersion"
            );
            super.preparePlugins();
        },
    });
});

test("can get content of an Editor", async () => {
    const { el, editor } = await setupEditor("<p>hel[lo] world</p>", {});
    expect(el.innerHTML).toBe(`<p>hello world</p>`);
    expect(editor.getContent()).toBe(`<p>hello world</p>`);
});

test("can get content of an empty paragraph", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>", {});
    expect(el.innerHTML).toBe(
        `<p o-we-hint-text="Type &quot;/&quot; for commands" class="o-we-hint"></p>`
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
    function makeTestPlugin(id, dependencies = []) {
        return class TestPlugin extends Plugin {
            static id = id;
            static dependencies = dependencies;

            setup() {
                expect.step(`setup: ${id}`);
            }
            destroy() {
                expect.step(`destroy: ${id}`);
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
        static id = "test";
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

test("Element is not editable if any plugin marks it non-editable", async () => {
    class TestPlugin extends Plugin {
        static id = "test";
        resources = {
            is_node_editable_predicates: (node) => {
                if (node.classList.contains("o-will-break-if-edited")) {
                    return false;
                }
            },
        };
    }
    const Plugins = [...MAIN_PLUGINS, TestPlugin];
    const { el, plugins } = await setupEditor(
        `<div>[<img class="o-editable-media o-will-break-if-edited">]</div>`,
        {
            config: { Plugins },
        }
    );
    const img = el.querySelector(".o-editable-media");
    const selectionPlugin = plugins.get("selection");
    await expect(selectionPlugin.isNodeEditable(img)).toBe(false);
});

test("clean_for_save_listeners is done last", async () => {
    // This test uses custom elements tag `c-div` to make sure they won't fall into
    // a case where they won't be merged anyway.
    // Without the proper fix, this test fails with sibling elements `c-div` merged together
    class TestPlugin extends Plugin {
        static id = "test";
        resources = {
            clean_for_save_handlers: ({ root }) => {
                for (const el of root.querySelectorAll("c-div")) {
                    el.removeAttribute("class");
                }
            },
        };
        setup() {
            for (const el of this.editable.querySelectorAll("c-div")) {
                el.classList.add("oe_unbreakable");
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

test("Convert self closing elements to opening/closing tags", async () => {
    await testEditor({
        contentBefore: unformat(`
            <div>
                <center t-if="ctx">
                    <pre t-out="ctx"/>
                </center>
                <t t-else="">
                    <b t-out="name"/>
                    <span t-out="name"/>
                    <a href="xyz" t-out="xyz"/>
                    <t t-out="object.partner_id" data-oe-t-inline="true"/>
                </t>
                <i t-out="ctx"/>
            </div>
        `),
        contentBeforeEdit: unformat(`
            <p data-selection-placeholder=""><br></p>
            <div>
                <center t-if="ctx">
                    <pre t-out="ctx"></pre>
                </center>
                <t t-else="">
                    <b t-out="name"></b>
                    <span t-out="name"></span>
                    <a href="xyz" t-out="xyz"></a>
                    <t t-out="object.partner_id" data-oe-t-inline="true"></t>
                </t>
                <i t-out="ctx"></i>
            </div>
            <p data-selection-placeholder=""><br></p>
        `),
    });
});

test("Remove `width`, `height` attributes from image and apply them to style", async () => {
    const { el } = await setupEditor(`
        <div>
            <img src="#" width="50%" height="50%">
        </div>
    `);
    expect(el.innerHTML.trim().replace(/\s+/g, " ")).toBe(
        `<div class="o-paragraph"> <img src="#" style="width: 50%; height: 50%;"> </div>`
    );
});

test("Remove `width`, `height` attributes from image and apply them to style with default unit (px)", async () => {
    const { el } = await setupEditor(`
        <div>
            <img src="#" width="50" height="50">
        </div>
    `);
    expect(el.innerHTML.trim().replace(/\s+/g, " ")).toBe(
        `<div class="o-paragraph"> <img src="#" style="width: 50px; height: 50px;"> </div>`
    );
});
