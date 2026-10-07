import {
    contains as mailContains,
    defineMailModels,
    insertText,
    openFormView,
    start,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { contains, serverState } from "@web/../tests/web_test_helpers";

defineMailModels();
describe.current.tags("desktop");

test("insert emoji at end of word", async () => {
    await start();
    await openFormView("res.partner", serverState.partnerId, {
        arch: `<form><field name="name" widget="text_emojis"/></form>`,
    });
    await insertText("textarea#name_0", "Hello", { replace: true });
    await contains(".o_field_text_emojis button:count(1)").click();
    await contains('.o-Emoji[data-codepoints="😀"]:count(1)').click();
    await mailContains("textarea#name_0", { value: "Hello😀" });
});

test("insert emoji as new word", async () => {
    await start();
    await openFormView("res.partner", serverState.partnerId, {
        arch: `<form><field name="name" widget="text_emojis"/></form>`,
    });
    await insertText("textarea#name_0", "Hello ", { replace: true });
    await contains(".o_field_text_emojis button:count(1)").click();
    await contains('.o-Emoji[data-codepoints="😀"]:count(1)').click();
    await mailContains("textarea#name_0", { value: "Hello 😀" });
});
