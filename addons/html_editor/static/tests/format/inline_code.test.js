import { test } from "@odoo/hoot";
import { testEditor } from "../_helpers/editor";
import { deleteBackward, deleteForward } from "../_helpers/user_actions";

test("should merge successive inline code", async () => {
    await testEditor({
        contentBefore: `<p><code class="o_inline_code">first</code></p>[]<p><code class="o_inline_code">second</code></p>`,
        stepFunction: async (editor) => {
            deleteBackward(editor);
        },
        contentAfter: `<p><code class="o_inline_code">first[]second</code></p>`,
    });
});

test("should remove empty inline code (backspace)", async () => {
    await testEditor({
        contentBefore: `<p>abc<code class="o_inline_code">x[]</code>def</p>`,
        stepFunction: async (editor) => {
            deleteBackward(editor);
        },
        contentAfter: `<p>abc[]def</p>`,
    });
});

test("should remove empty inline code (delete)", async () => {
    await testEditor({
        contentBefore: `<p>abc<code class="o_inline_code">[]x</code>def</p>`,
        stepFunction: async (editor) => {
            deleteForward(editor);
        },
        contentAfter: `<p>abc[]def</p>`,
    });
});

test("should remove empty inline code from start of list entry", async () => {
    await testEditor({
        contentBefore: `<ul><li><code class="o_inline_code">x</code></li><li><code class="o_inline_code">y</code>[]abc</li></ul>`,
        stepFunction: async (editor) => {
            deleteBackward(editor);
        },
        contentAfter: `<ul><li><code class="o_inline_code">x</code></li><li>[]abc</li></ul>`,
    });
});
