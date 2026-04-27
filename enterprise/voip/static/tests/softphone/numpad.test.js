import { describe, expect, test } from "@odoo/hoot";
import { tick } from "@odoo/hoot-mock";
import {
    click,
    contains,
    insertText,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { setupVoipTests } from "@voip/../tests/voip_test_helpers";

describe.current.tags("desktop");
setupVoipTests();

test("Number input is focused when opening the numpad.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button[title='Open Numpad']");
    await contains("input[placeholder='Enter the number…']:focus");
});

test("Number input content is persisted when closing then re-opening the numpad.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button[title='Open Numpad']");
    await insertText("input[placeholder='Enter the number…']", "513");
    await click("button[title='Close Numpad']");
    await click("button[title='Open Numpad']");
    await contains("input[placeholder='Enter the number…'][data-value='513']");
});

test("Clicking on the “Backspace button” deletes the last character of the number input.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button[title='Open Numpad']");
    await insertText("input[placeholder='Enter the number…']", "123");
    await click("button[title='Backspace']");
    await contains("input[placeholder='Enter the number…'][data-value='12']");
});

test("Cursor is taken into account when clicking Backspace.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button[title='Open Numpad']");
    await insertText("input[placeholder='Enter the number…']", "01123456");
    const input = document.querySelector("input[placeholder='Enter the number…']");
    input.setSelectionRange(3, 3);
    await click("button[title='Backspace']");
    expect(input.selectionStart).toBe(2);
    expect(input.selectionEnd).toBe(2);
    await contains("input[data-value='0123456']");
});

test("Cursor range selection is taken into account when clicking Backspace.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button[title='Open Numpad']");
    await insertText("input[placeholder='Enter the number…']", "011123456");
    const input = document.querySelector("input[placeholder='Enter the number…']");
    input.setSelectionRange(2, 4);
    await click("button[title='Backspace']");
    expect(input.selectionStart).toBe(2);
    expect(input.selectionEnd).toBe(2);
    await contains("input[placeholder='Enter the number…'][data-value='0123456']");
});

test("Selection starting at the beginning is removed when clicking Backspace.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button[title='Open Numpad']");
    await insertText("input[placeholder='Enter the number…']", "0123456");
    const input = document.querySelector("input[placeholder='Enter the number…']");
    input.setSelectionRange(0, 2);
    await click("button[title='Backspace']");
    expect(input.selectionStart).toBe(0);
    expect(input.selectionEnd).toBe(0);
    await contains("input[placeholder='Enter the number…']", { value: "23456" });
});

test("When cursor is at the beginning of the input, clicking Backspace does nothing.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button[title='Open Numpad']");
    await insertText("input[placeholder='Enter the number…']", "0123456");
    const input = document.querySelector("input[placeholder='Enter the number…']");
    input.setSelectionRange(0, 0);
    await click("button[title='Backspace']");
    expect(input.selectionStart).toBe(0);
    expect(input.selectionEnd).toBe(0);
    await contains("input[placeholder='Enter the number…'][data-value='0123456']");
});

test("Clicking on a key appends it to the number input.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button[title='Open Numpad']");
    await insertText("input[placeholder='Enter the number…']", "123");
    await click("button", { text: "#" });
    await tick();
    await contains("input[placeholder='Enter the number…'][data-value='123#']");
});

test("Number input is focused after clicking on a key.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button[title='Open Numpad']");
    await click("button", { text: "2" });
    await tick();
    await contains("input[placeholder='Enter the number…']:focus");
});

test("Cursor is taken into account when clicking on a key.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button[title='Open Numpad']");
    await insertText("input[placeholder='Enter the number…']", "023456");
    const input = document.querySelector("input[placeholder='Enter the number…']");
    input.setSelectionRange(1, 1);
    await click("button", { text: "1" });
    expect(input.selectionStart).toBe(2);
    expect(input.selectionEnd).toBe(2);
    await contains("input[placeholder='Enter the number…'][data-value='0123456']");
});

test("Cursor range selection is taken into account when clicking on a key.", async () => {
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button[title='Open Numpad']");
    await insertText("input[placeholder='Enter the number…']", "0223456");
    const input = document.querySelector("input[placeholder='Enter the number…']");
    input.setSelectionRange(1, 2);
    await click("button", { text: "1" });
    expect(input.selectionStart).toBe(2);
    expect(input.selectionEnd).toBe(2);
    await contains("input[placeholder='Enter the number…'][data-value='0123456']");
});

test("Pressing Enter in the input makes a call to the dialed number.", async () => {
    const pyEnv = await startServer();
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button[title='Open Numpad']");
    await contains("input[placeholder='Enter the number…']");
    await insertText("input[placeholder='Enter the number…']", "9223372036854775807");
    await triggerHotkey("Enter");
    expect(pyEnv["voip.call"].search_count([["phone_number", "=", "9223372036854775807"]])).toBe(1);
});

test("Pressing Enter in the input doesn't make a call if the trimmed input is empty string.", async () => {
    const pyEnv = await startServer();
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button[title='Open Numpad']");
    await insertText("input[placeholder='Enter the number…']", "\t \n\r\v");
    await triggerHotkey("Enter");
    expect(pyEnv["voip.call"].search_count([])).toBe(0);
});
