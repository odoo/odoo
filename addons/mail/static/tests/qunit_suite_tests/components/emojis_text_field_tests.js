/**@odoo-module **/

import { getFixture } from "@web/../tests/helpers/utils";
import { start, startServer } from "@mail/../tests/helpers/test_utils";
import { addFakeModel } from "@bus/../tests/helpers/model_definitions_helpers";

import { testEmojiButton, testEmojiButtonVisible } from "./emojis_field_common_tests";

QUnit.module("Field text emojis", (hooks) => {
    let target = undefined;

    addFakeModel("fields.text.emojis.user", {
        foo: { type: "char", onChange: "1" },
    });
    const views = {
        "fields.text.emojis.user,false,form": `
            <form>
                <field name="foo" widget="text_emojis"/>
            </form>
        `,
    };
    const openTestView = async () => {
        const pyEnv = await startServer();
        const recordId = pyEnv["fields.text.emojis.user"].create({
            display_name: "test record",
            foo: "test",
        });
        const startServerArgs = { serverData: { views } };
        const openViewArgs = {
            res_id: recordId,
            res_model: "fields.text.emojis.user",
            views: [[false, "form"]],
        };
        const { openView } = await start(startServerArgs);
        await openView(openViewArgs);
    };

    hooks.beforeEach(() => {
        target = getFixture();
    });

    QUnit.test("emojis button is shown", async (assert) => {
        await openTestView();
        await testEmojiButtonVisible(assert, target, ".o_field_text_emojis");
    });

    QUnit.test("emojis button works", async (assert) => {
        await openTestView();

        const input = target.querySelector(".o_field_text_emojis textarea");
        const emojiButton = target.querySelector(".o_field_text_emojis button");

        await testEmojiButton(assert, target, input, emojiButton);
    });
});
