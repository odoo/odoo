/**@odoo-module **/

import { start, startServer } from "@mail/../tests/helpers/test_utils";
import { addFakeModel } from "@bus/../tests/helpers/model_definitions_helpers";
import { click } from "@web/../tests/helpers/utils";

/**
 * Check that the emoji button is not visible
 *
 * @param {object} assert the assert object passed by QUnit
 * @param {string} emojiComponentSelector unique selector to get the component template root (e.g. ".o_field_text_emojis")
 */
export async function testEmojiButtonHidden(assert, selector) {
    assert.containsOnce($, ".o_form_readonly");
    assert.containsOnce($, selector);
    assert.containsNone($, `${selector} button`);
}

/**
 * Check that the emoji button is visible
 *
 * @param {object} assert the assert object passed by QUnit
 * @param {string} emojiComponentSelector unique selector to get the component template root (e.g. "o_field_text_emojis")
 */
export async function testEmojiButtonVisible(assert, selector) {
    assert.containsOnce($, ".o_form_editable");
    assert.containsOnce($, selector);
    assert.containsOnce($, `${selector} button`);
    assert.containsOnce($, `${selector} button .fa-smile-o`);
}

/**
 * Quick test to make sure basic functionalities work for fields that use emoji_text_field_view.
 *
 * @param {object} assert the assert object passed by QUnit
 * @param {HTMLElement} input a reference to the input element (input[type="text"], textarea, ...)
 * @param {HTMLElement} button a reference to the trigger button element
 */
export async function testEmojiButton(assert, input, button) {
    // emoji picker opens
    await click(button);
    assert.containsOnce($, ".o-mail-EmojiPicker");
    // clicking an emoji adds it to the input field
    const emoji_1 = $(".o-mail-EmojiPicker-content .o-mail-Emoji")[0];
    const emojiChar_1 = emoji_1.textContent;
    await click(emoji_1);
    assert.ok(input.value.endsWith(emojiChar_1));
    // add some text at the start and select from the second half of the word to right before the emoji we just inserted
    input.value = "test" + input.value;
    input.setSelectionRange(2, input.value.length - emojiChar_1.length);
    // pick an emoji while the text is selected
    await click(button);
    const emoji_2 = $(".o-mail-EmojiPicker-content .o-mail-Emoji")[0];
    const emojiChar_2 = emoji_2.textContent;
    await click(emoji_2);
    // the selected region is replaced and the rest stays in place
    assert.deepEqual(input.value, "te" + emojiChar_2 + emojiChar_1);
}

addFakeModel("fields.char.emojis.user", { foo: { type: "char", onChange: "1" } });
addFakeModel("fields.text.emojis.user", { foo: { type: "char", onChange: "1" } });

const views = {
    "fields.char.emojis.user,false,form": `
        <form>
            <field name="foo" widget="char_emojis"/>
        </form>`,
    "fields.text.emojis.user,false,form": `
        <form>
            <field name="foo" widget="text_emojis"/>
        </form>
    `,
};

async function openTestView(model, readonly = false) {
    const pyEnv = await startServer();
    const recordId = pyEnv[model].create({
        display_name: "test record",
        foo: "test",
    });
    const openViewArgs = {
        res_id: recordId,
        res_model: model,
        views: [[false, "form"]],
    };
    if (readonly) {
        openViewArgs.context = { form_view_initial_mode: "readonly" };
    }
    const { openView } = await start({ serverData: { views } });
    await openView(openViewArgs);
}

QUnit.module("Field char emojis");

QUnit.test("emojis button is not shown in readonly mode", async (assert) => {
    await openTestView("fields.char.emojis.user", true);
    await testEmojiButtonHidden(assert, ".o_field_char_emojis");
});

QUnit.test("emojis button is shown in edit mode", async (assert) => {
    await openTestView("fields.char.emojis.user");
    await testEmojiButtonVisible(assert, ".o_field_char_emojis");
});

QUnit.test("emojis button works", async (assert) => {
    await openTestView("fields.char.emojis.user");
    const input = $(".o_field_char_emojis input[type='text']")[0];
    const emojiButton = $(".o_field_char_emojis button")[0];
    await testEmojiButton(assert, input, emojiButton);
});

QUnit.module("Field text emojis");

QUnit.test("emojis button is not shown in readonly mode", async (assert) => {
    await openTestView("fields.text.emojis.user", true);
    await testEmojiButtonHidden(assert, ".o_field_text_emojis");
});

QUnit.test("emojis button is shown in edit mode", async (assert) => {
    await openTestView("fields.text.emojis.user");
    await testEmojiButtonVisible(assert, ".o_field_text_emojis");
});

QUnit.test("emojis button works", async (assert) => {
    await openTestView("fields.text.emojis.user");
    const input = $(".o_field_text_emojis textarea")[0];
    const emojiButton = $(".o_field_text_emojis button")[0];
    await testEmojiButton(assert, input, emojiButton);
});
