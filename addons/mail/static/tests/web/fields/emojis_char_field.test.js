import {
    click,
    contains,
    defineMailModels,
    insertText,
    openFormView,
    start,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { serverState } from "@web/../tests/web_test_helpers";

defineMailModels();
describe.current.tags("desktop");

test("insert emoji at end of word", async () => {
    await start();
    await openFormView("res.partner", serverState.partnerId, {
        arch: `<form><field name="name" widget="char_emojis"/></form>`,
    });
    await insertText("input#name_0", "Hello", { replace: true });
    await click(".o_field_char_emojis button");
    await click('.o-Emoji[data-codepoints="😀"]');
    await contains("input#name_0", { value: "Hello😀" });
});

test("insert emoji as new word", async () => {
    await start();
    await openFormView("res.partner", serverState.partnerId, {
        arch: `<form><field name="name" widget="char_emojis"/></form>`,
    });
    await insertText("input#name_0", "Hello ", { replace: true });
    await click(".o_field_char_emojis button");
    await click('.o-Emoji[data-codepoints="😀"]');
    await contains("input#name_0", { value: "Hello 😀" });
});
