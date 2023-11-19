import { expect, test } from "@odoo/hoot";
import { setupEditor } from "./_helpers/editor";
import { insertText } from "./_helpers/user_actions";

test("can get content of an Editor", async () => {
    const { el, editor } = await setupEditor("<p>hel[lo] world</p>", {});
    expect(el.innerHTML).toBe(`<p>hello world</p>`);
    expect(editor.getContent()).toBe(`<p>hello world</p>`)
});

test("can get content of an empty paragraph", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>", {});
    expect(el.innerHTML).toBe(`<p placeholder="Type &quot;/&quot; for commands" class="o-we-hint"></p>`);
    expect(editor.getContent()).toBe(`<p></p>`)
});

test("is notified when content is changed", async () => {
    let n = 0
    const { editor } = await setupEditor("<p>hello[] world</p>", {
        config: { onChange: () => n++}
    });
    expect(n).toBe(0);
    insertText(editor, "a")

    expect(editor.getContent()).toBe(`<p>helloa world</p>`)
    expect(n).toBe(1)
});
