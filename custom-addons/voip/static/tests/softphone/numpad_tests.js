/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { nextTick, triggerHotkey } from "@web/../tests/helpers/utils";
import { click, contains, insertText } from "@web/../tests/utils";

QUnit.module("numpad");

QUnit.test("Number input is focused when opening the numpad.", async () => {
    start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button[title='Open Numpad']");
    await contains("input[placeholder='Enter the number…']:focus");
});

QUnit.test(
    "Number input content is persisted when closing then re-opening the numpad.",
    async () => {
        start();
        await click(".o_menu_systray button[title='Open Softphone']");
        await click("button[title='Open Numpad']");
        await insertText("input[placeholder='Enter the number…']", "513");
        await click("button[title='Close Numpad']");
        await click("button[title='Open Numpad']");
        await contains("input[placeholder='Enter the number…']", { value: "513" });
    }
);

QUnit.test(
    "Clicking on the “Backspace button” deletes the last character of the number input.",
    async () => {
        start();
        await click(".o_menu_systray button[title='Open Softphone']");
        await click("button[title='Open Numpad']");
        await insertText("input[placeholder='Enter the number…']", "123");
        await click("button[title='Backspace']");
        await nextTick();
        await contains("input[placeholder='Enter the number…']", { value: "12" });
    }
);

QUnit.test(
    "Cursor is taken into account when clicking Backspace.",
    async (assert) => {
        start();
        await click(".o_menu_systray button[title='Open Softphone']");
        await click("button[title='Open Numpad']");
        await insertText("input[placeholder='Enter the number…']", "01123456");
        const input = document.querySelector("input[placeholder='Enter the number…']");
        input.setSelectionRange(3, 3);
        await click("button[title='Backspace']");
        assert.strictEqual(input.selectionStart, 2);
        assert.strictEqual(input.selectionEnd, 2);
        await contains("input[placeholder='Enter the number…']", { value: "0123456" });
    }
);

QUnit.test(
    "Cursor range selection is taken into account when clicking Backspace.",
    async (assert) => {
        start();
        await click(".o_menu_systray button[title='Open Softphone']");
        await click("button[title='Open Numpad']");
        await insertText("input[placeholder='Enter the number…']", "011123456");
        const input = document.querySelector("input[placeholder='Enter the number…']");
        input.setSelectionRange(2, 4);
        await click("button[title='Backspace']");
        assert.strictEqual(input.selectionStart, 2);
        assert.strictEqual(input.selectionEnd, 2);
        await contains("input[placeholder='Enter the number…']", { value: "0123456" });
    }
);

QUnit.test(
    "When cursor is at the beginning of the input, clicking Backspace does nothing.",
    async (assert) => {
        start();
        await click(".o_menu_systray button[title='Open Softphone']");
        await click("button[title='Open Numpad']");
        await insertText("input[placeholder='Enter the number…']", "0123456");
        const input = document.querySelector("input[placeholder='Enter the number…']");
        input.setSelectionRange(0, 0);
        await click("button[title='Backspace']");
        assert.strictEqual(input.selectionStart, 0);
        assert.strictEqual(input.selectionEnd, 0);
        await contains("input[placeholder='Enter the number…']", { value: "0123456" });
    }
);

QUnit.test("Clicking on a key appends it to the number input.", async () => {
    start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button[title='Open Numpad']");
    await insertText("input[placeholder='Enter the number…']", "123");
    await click("button", { text: "#" });
    await nextTick();
    await contains("input[placeholder='Enter the number…']", { value: "123#" });
});

QUnit.test("Number input is focused after clicking on a key.", async () => {
    start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button[title='Open Numpad']");
    await click("button", { text: "2" });
    await nextTick();
    await contains("input[placeholder='Enter the number…']:focus");
});

QUnit.test(
    "Cursor is taken into account when clicking on a key.",
    async (assert) => {
        start();
        await click(".o_menu_systray button[title='Open Softphone']");
        await click("button[title='Open Numpad']");
        await insertText("input[placeholder='Enter the number…']", "023456");
        const input = document.querySelector("input[placeholder='Enter the number…']");
        input.setSelectionRange(1, 1);
        await click("button", { text: "1" });
        assert.strictEqual(input.selectionStart, 2);
        assert.strictEqual(input.selectionEnd, 2);
        await contains("input[placeholder='Enter the number…']", { value: "0123456" });
    }
);

QUnit.test(
    "Cursor range selection is taken into account when clicking on a key.",
    async (assert) => {
        start();
        await click(".o_menu_systray button[title='Open Softphone']");
        await click("button[title='Open Numpad']");
        await insertText("input[placeholder='Enter the number…']", "0223456");
        const input = document.querySelector("input[placeholder='Enter the number…']");
        input.setSelectionRange(1, 2);
        await click("button", { text: "1" });
        assert.strictEqual(input.selectionStart, 2);
        assert.strictEqual(input.selectionEnd, 2);
        await contains("input[placeholder='Enter the number…']", { value: "0123456" });
    }
);

QUnit.test("Pressing Enter in the input makes a call to the dialed number.", async (assert) => {
    const pyEnv = await startServer();
    start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button[title='Open Numpad']");
    await contains("input[placeholder='Enter the number…']");
    await insertText("input[placeholder='Enter the number…']", "9223372036854775807");
    await triggerHotkey("Enter");
    assert.strictEqual(
        pyEnv["voip.call"].searchCount([["phone_number", "=", "9223372036854775807"]]),
        1
    );
});

QUnit.test(
    "Pressing Enter in the input doesn't make a call if the trimmed input is empty string.",
    async (assert) => {
        const pyEnv = await startServer();
        start();
        await click(".o_menu_systray button[title='Open Softphone']");
        await click("button[title='Open Numpad']");
        await insertText("input[placeholder='Enter the number…']", "\t \n\r\v");
        await triggerHotkey("Enter");
        assert.strictEqual(pyEnv["voip.call"].searchCount([]), 0);
    }
);
