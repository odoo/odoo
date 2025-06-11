import { test } from "@odoo/hoot";
import { testEditor } from "./_helpers/editor";

test("should remove comment node inside editable content during sanitize", async () => {
    await testEditor({
        contentBefore: "<p>ab<!-- comment -->cd</p>",
        contentAfter: "<p>abcd</p>",
    });
    await testEditor({
        contentBefore: "<p>ab<!-- comment -->cd<!-- Another comment --></p>",
        contentAfter: "<p>abcd</p>",
    });
});
