/** @odoo-module **/

import { click, editInput } from '@web/../tests/helpers/utils';
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;

QUnit.module('mail', {}, () => {
QUnit.module('widgets', {}, (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        qux: { string: "Qux", type: "char", trim: true }
                    }
                }
            }
        }
        setupViewRegistries();
    });

    QUnit.module("emojis_char_field_tests.js");

    QUnit.test("emojis_char_field_tests widget: insert emoji at end of word", async function (assert) {
        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <field name="qux" widget="char_emojis"/>
                </form>
            `,
        });

        const inputName = document.querySelector('input#qux')
        await editInput(inputName, null, "Hello");
        assert.strictEqual(inputName.value, "Hello");

        click(document, '.o_mail_add_emoji button');
        click(document, '.o_mail_emoji[data-emoji=":)"]');
        assert.strictEqual(inputName.value, "Hello😊");
    });

    QUnit.test("emojis_char_field_tests widget: insert emoji as new word", async function (assert) {
        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <field name="qux" widget="char_emojis"/>
                </form>
            `,
        });

        const inputName = document.querySelector('input#qux')
        await editInput(inputName, null, "Hello ");
        assert.strictEqual(inputName.value, "Hello ");

        click(document, '.o_mail_add_emoji button');
        click(document, '.o_mail_emoji[data-emoji=":)"]');
        assert.strictEqual(inputName.value, "Hello 😊");
    });


});
});
