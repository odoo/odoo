import { Plugin } from "@html_editor/plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { setupEditor, testEditor } from "./_helpers/editor";
import { getContent, setContent } from "./_helpers/selection";

test("can instantiate a Editor", async () => {
    const { el, editor } = await setupEditor("<p>hel[lo] world</p>", {});
    expect(el.innerHTML).toBe(`<p>hello world</p>`);
    expect(getContent(el)).toBe(`<p>hel[lo] world</p>`);
    setContent(el, "<div>a[dddb]</div>");
    editor.dispatch("FORMAT_BOLD");
    expect(getContent(el)).toBe(`<div>a<strong>[dddb]</strong></div>`);
});

test("cannot reattach an editor", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>", {});
    expect(getContent(el)).toBe(`<p placeholder='Type "/" for commands' class="o-we-hint">[]</p>`);
    expect(() => editor.attachTo(el)).toThrow("Cannot re-attach an editor");
});

test("cannot reattach a destroyed editor", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>", {});
    expect(getContent(el)).toBe(`<p placeholder='Type "/" for commands' class="o-we-hint">[]</p>`);
    editor.destroy();
    expect(getContent(el)).toBe(`<p>[]</p>`);
    expect(() => editor.attachTo(el)).toThrow("Cannot re-attach an editor");
});

test.tags("iframe")("can instantiate a Editor in an iframe", async () => {
    const { el, editor } = await setupEditor("<p>hel[lo] world</p>", { props: { iframe: true } });
    expect("iframe").toHaveCount(1);
    expect(el.innerHTML).toBe(`<p>hello world</p>`);
    expect(getContent(el)).toBe(`<p>hel[lo] world</p>`);
    setContent(el, "<div>a[dddb]</div>");
    editor.dispatch("FORMAT_BOLD");
    expect(getContent(el)).toBe(`<div>a<strong>[dddb]</strong></div>`);
});

test("with an empty selector", async () => {
    const { el } = await setupEditor("<div>[]</div>", {});
    expect(el.innerHTML).toBe(
        `<div placeholder="Type &quot;/&quot; for commands" class="o-we-hint"></div>`
    );
    expect(getContent(el)).toBe(
        `<div placeholder='Type "/" for commands' class="o-we-hint">[]</div>`
    );
});

test("with a part of the selector in an empty HTMLElement", async () => {
    const { el } = await setupEditor("<div>a[bc<div>]</div></div>", {});
    expect(el.innerHTML).toBe(`<div>abc<div></div></div>`);
    expect(getContent(el)).toBe(`<div>a[bc<div>]</div></div>`);
});

test("inverse selection", async () => {
    const { el } = await setupEditor("<div>a]bc<div>[</div></div>", {});
    expect(el.innerHTML).toBe(`<div>abc<div></div></div>`);
    expect(getContent(el)).toBe(`<div>a]bc<div>[</div></div>`);
});

test("with an empty selector and a <br>", async () => {
    const { el } = await setupEditor("<p>[]<br></p>", {});
    expect(getContent(el)).toBe(
        `<p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>`
    );
});

test("no arrow key press or mouse click should keep selection near a contenteditable='false'", async () => {
    await testEditor({
        contentBefore: '[]<hr contenteditable="false">',
        contentAfter: "[]<hr>",
    });
    await testEditor({
        contentBefore: '<hr contenteditable="false">[]',
        contentAfter: "<hr>[]",
    });
});

test("event handlers are properly cleaned up after destruction", async () => {
    let count = 0;
    class TestHandlerPlugin extends Plugin {
        static name = "test_handler";

        setup() {
            this.addDomListener(document.body, "click", () => count++);
        }
    }

    const { editor } = await setupEditor("<p></p>", {
        config: { Plugins: [...MAIN_PLUGINS, TestHandlerPlugin] },
    });
    expect(count).toBe(0);

    await click(document.body);
    expect(count).toBe(1);

    editor.destroy();
    await click(document.body);
    expect(count).toBe(1);
});

test("can give resources in config", async () => {
    expect.assertions(1);
    class TestPlugin extends Plugin {
        static name = "test";

        setup() {
            expect(this.resources.some).toEqual(["value"]);
        }
    }

    await setupEditor("<p></p>", {
        config: {
            Plugins: [...MAIN_PLUGINS, TestPlugin],
            resources: { some: ["value"] },
        },
    });
});
