/**@odoo-module **/

import { getFixture } from "@web/../tests/helpers/utils";
import { start, startServer } from "@mail/../tests/helpers/test_utils";
import { addFakeModel } from "@bus/../tests/helpers/model_definitions_helpers";
import {
    testEmojiButton,
    testEmojiButtonHidden,
    testEmojiButtonVisible,
} from "./emojis_field_common_tests";

let target = undefined;

addFakeModel("fields.char.emojis.user", { foo: { type: "char", onChange: "1" } });
const views = {
    "fields.char.emojis.user,false,form": `
        <form>
            <field name="foo" widget="char_emojis"/>
        </form>
    `,
};

async function openTestView(readonly = false) {
    const pyEnv = await startServer();
    const recordId = pyEnv["fields.char.emojis.user"].create({
        display_name: "test record",
        foo: "test",
    });
    const openViewArgs = {
        res_id: recordId,
        res_model: "fields.char.emojis.user",
        views: [[false, "form"]],
    };
    if (readonly) {
        openViewArgs.context = { form_view_initial_mode: "readonly" };
    }
    const { openView } = await start({ serverData: { views } });
    await openView(openViewArgs);
}

QUnit.module("Field char emojis", {
    beforeEach() {
        target = getFixture();
    },
});

QUnit.test("emojis button is not shown in readonly mode", async (assert) => {
    await openTestView(true);
    await testEmojiButtonHidden(assert, target, ".o_field_char_emojis");
});

QUnit.test("emojis button is shown in edit mode", async (assert) => {
    await openTestView();
    await testEmojiButtonVisible(assert, target, ".o_field_char_emojis");
});

QUnit.test("emojis button works", async (assert) => {
    await openTestView();
    const input = target.querySelector(".o_field_char_emojis input[type='text']");
    const emojiButton = target.querySelector(".o_field_char_emojis button");
    await testEmojiButton(assert, target, input, emojiButton);
});
