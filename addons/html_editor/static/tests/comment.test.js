import { test } from "@odoo/hoot";
import { testEditor } from "./_helpers/editor";

test("should remove comment node inside editable content during sanitize (1)", async () => {
    await testEditor({
        contentBefore: "<p>ab<!-- comment -->cd</p>",
        contentAfter: "<p>abcd</p>",
    });
});

test("should remove comment node inside editable content during sanitize (2)", async () => {
    await testEditor({
        contentBefore: "<p>ab<!-- comment -->cd<!-- Another comment --></p>",
        contentAfter: "<p>abcd</p>",
    });
});
