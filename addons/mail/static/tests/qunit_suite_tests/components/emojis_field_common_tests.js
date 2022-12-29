/**@odoo-module **/

import { click } from "@web/../tests/helpers/utils";

/**
 * Check that the emoji button is not visible
 *
 * @param {object} assert the assert object passed by QUnit
 * @param {HTMLElement} target fixture where the view is displayed
 * @param {string} emojiComponentSelector unique selector to get the component template root (e.g. ".o_field_text_emojis")
 */
export async function testEmojiButtonHidden(assert, target, emojiComponentSelector) {
    assert.containsOnce(target, ".o_form_readonly");
    assert.containsOnce(target, emojiComponentSelector);
    assert.containsNone(target, `${emojiComponentSelector} button`);
}

/**
 * Check that the emoji button is visible
 *
 * @param {object} assert the assert object passed by QUnit
 * @param {HTMLElement} target fixture where the view is displayed
 * @param {string} emojiComponentSelector unique selector to get the component template root (e.g. "o_field_text_emojis")
 */
export async function testEmojiButtonVisible(assert, target, emojiComponentSelector) {
    assert.containsOnce(target, ".o_form_editable");
    assert.containsOnce(target, emojiComponentSelector);
    assert.containsOnce(target, `${emojiComponentSelector} button`);
    assert.containsOnce(target, `${emojiComponentSelector} button .fa-smile-o`);
}

/**
 * Quick test to make sure basic functionalities work for fields that use emoji_text_field_view.
 *
 * @param {object} assert the assert object passed by QUnit
 * @param {HTMLElement} target fixture where the view is displayed
 * @param {HTMLElement} input a reference to the input element (input[type="text"], textarea, ...)
 * @param {HTMLElement} emojiButton a reference to the trigger button element
 */
export async function testEmojiButton(assert, target, input, emojiButton) {
    // emoji picker opens
    await click(emojiButton);
    assert.containsOnce(target, ".o-mail-emoji-picker");
    // clicking an emoji adds it to the input field
    const firstEmojiItem = target.querySelector(".o-mail-emoji-picker-content .o-emoji");
    const firstEmojiItemCharacter = firstEmojiItem.textContent;
    await click(firstEmojiItem);
    assert.ok(
        input.value.endsWith(firstEmojiItemCharacter),
        "Should have added the right emoji in the input field"
    );
    // add some text at the start and select from the second half of the word to right before the emoji we just inserted
    input.value = "test" + input.value;
    const inputTextLength = input.value.length;
    input.setSelectionRange(2, inputTextLength - firstEmojiItemCharacter.length);
    // pick an emoji while the text is selected
    await click(emojiButton);
    const secondEmojiItem = target.querySelector(".o-mail-emoji-picker-content .o-emoji");
    const secondEmojiItemCharacter = secondEmojiItem.textContent;
    await click(secondEmojiItem);
    // the selected region is replaced and the rest stays in place
    assert.deepEqual(
        input.value,
        "te" + secondEmojiItemCharacter + firstEmojiItemCharacter,
        "Should have replaced the selection with the emoji"
    );
}
