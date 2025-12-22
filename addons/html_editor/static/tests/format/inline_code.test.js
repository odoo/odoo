import { test } from "@odoo/hoot";
import { testEditor } from "../_helpers/editor";
import { deleteBackward } from "../_helpers/user_actions";

test("should merge successive inline code", async () => {
    await testEditor({
        contentBefore: `<p><code class="o_inline_code">first</code></p>[]<p><code class="o_inline_code">second</code></p>`,
        stepFunction: async (editor) => {
            deleteBackward(editor);
        },
        contentAfter: `<p><code class="o_inline_code">first[]second</code></p>`,
    });
});
