/** @odoo-module **/

import { click, editInput, nextTick } from "@web/../tests/helpers/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";
import { start } from "@mail/../tests/helpers/test_utils";
import { addFakeModel } from "@bus/../tests/helpers/model_definitions_helpers";

let serverData;

QUnit.module("mail", {}, () => {
QUnit.module("widgets", {}, (hooks) => {
    addFakeModel("mailing.mailing", {
        subject: { string: "Subject", type: "char", trim: true }
    });

    hooks.beforeEach(() => {
        serverData = {
            views: {
                "mailing.mailing,false,form": `
                    <form>
                        <field name="subject" widget="char_emojis"/>
                    </form>
                `
            },
        }
        setupViewRegistries();
    });

    QUnit.module("emojis_char_field_tests.js");

    QUnit.test("emojis_char_field_tests widget: insert emoji at end of word", async function (assert) {
        assert.expect(2);
        const {openFormView} =  await start({serverData});
        await openFormView({res_model: "mailing.mailing"}, {
            waitUntilDataLoaded: false, waitUntilMessagesLoaded: false});

        const inputName = document.querySelector("input#subject");
        await editInput(inputName, null, "Hello");
        assert.strictEqual(inputName.value, "Hello");

        click(document, ".o_field_char_emojis button");
        await nextTick();
        click(document, '.o_EmojiView[data-codepoints="😀"]');
        assert.strictEqual(inputName.value, "Hello😀");
    });

    QUnit.test("emojis_char_field_tests widget: insert emoji as new word", async function (assert) {
        assert.expect(2);
        const {openFormView} =  await start({serverData});
        await openFormView({res_model: "mailing.mailing"}, {
            waitUntilDataLoaded: false, waitUntilMessagesLoaded: false});

        const inputName = document.querySelector("input#subject");
        await editInput(inputName, null, "Hello ");
        assert.strictEqual(inputName.value, "Hello ");

        click(document, ".o_field_char_emojis button");
        await nextTick();
        click(document, '.o_EmojiView[data-codepoints="😀"]');
        assert.strictEqual(inputName.value, "Hello 😀");
    });


});
});
