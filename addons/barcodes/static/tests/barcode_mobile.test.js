/** @odoo-module **/

import { beforeEach, expect, test } from "@odoo/hoot";
import {
    advanceTime,
    click,
    getActiveElement,
    keyDown,
    manuallyDispatchProgrammaticEvent,
    queryFirst,
} from "@odoo/hoot-dom";
import { getService, mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { barcodeService } from "@barcodes/barcode_service";
import { Component, xml } from "@odoo/owl";

beforeEach(() => {
    patchWithCleanup(barcodeService, {
        maxTimeBetweenKeysInMs: 0,
        isMobileChrome: true,
    });
});
class Root extends Component {
    static template = xml`
    <form>
        <input name="email" type="email"/>
        <input name="number" type="number"/>
        <input name="password" type="password"/>
        <input name="tel" type="tel"/>
        <input name="text"/>
        <input name="explicit_text" type="text"/>
        <textarea></textarea>
        <div contenteditable="true"></div>
        <select name="select">
            <option value="option1">Option 1</option>
            <option value="option2">Option 2</option>
        </select>
    </form>`;
    static props = ["*"];
}

/**
 * Types a character the way an Android IME does: the keydown event carries no
 * key, only the following input event tells that a character was inserted.
 */
async function imeInput(char) {
    const input = getActiveElement();
    await keyDown("Unidentified");
    input.value += char;
    await manuallyDispatchProgrammaticEvent(input, "input", {
        data: char,
        inputType: "insertText",
    });
}

test.tags("mobile");
test("barcode field automatically focus behavior", async () => {
    expect.assertions(10);
    await mountWithCleanup(Root);

    // Some elements doesn't need to keep the focus
    await click(document.body);
    await keyDown("a");
    expect(getActiveElement()).toHaveProperty("name", "barcode", {
        message: "hidden barcode input should have the focus",
    });

    let element = queryFirst("select");
    await click(element);
    await keyDown("b");
    expect(getActiveElement()).toHaveProperty("name", "barcode", {
        message: "hidden barcode input should have the focus",
    });

    // Those elements absolutely need to keep the focus:
    // inputs elements:
    const keepFocusedElements = ["email", "number", "password", "tel", "text", "explicit_text"];
    for (let i = 0; i < keepFocusedElements.length; ++i) {
        element = queryFirst(`input[name=${keepFocusedElements[i]}]`);
        await click(element);
        await keyDown("c");
        expect(`input[name=${keepFocusedElements[i]}]`).toBeFocused({
            message: `input ${keepFocusedElements[i]} should keep focus`,
        });
    }
    // textarea element
    element = queryFirst(`textarea`);
    await click(element);
    await keyDown("d");
    expect(`textarea`).toBeFocused({ message: "textarea should keep focus" });
    // contenteditable elements
    element = queryFirst(`[contenteditable=true]`);
    await click(element);
    await keyDown("e");
    expect(`[contenteditable=true]`).toBeFocused({
        message: "contenteditable should keep focus",
    });
});

test.tags("mobile");
test("IME input in the hidden barcode input does not split the barcode", async () => {
    patchWithCleanup(barcodeService, { maxTimeBetweenKeysInMs: 50 });
    await mountWithCleanup(Root);
    getService("barcode").bus.addEventListener("barcode_scanned", ({ detail }) =>
        expect.step(detail.barcode)
    );

    // Only the first key is a genuine key event: it gives the focus to the
    // hidden input, the next ones go through the IME.
    await click(document.body);
    await keyDown("8");
    for (const char of "901086261410") {
        await advanceTime(20);
        await imeInput(char);
    }
    await keyDown("Enter");
    expect.verifySteps(["8901086261410"]);
});

test.tags("mobile");
test("barcode without end character is scanned after the delay following the last IME input", async () => {
    patchWithCleanup(barcodeService, { maxTimeBetweenKeysInMs: 50 });
    await mountWithCleanup(Root);
    getService("barcode").bus.addEventListener("barcode_scanned", ({ detail }) =>
        expect.step(detail.barcode)
    );

    await click(document.body);
    await keyDown("Enter");
    expect(getActiveElement()).toHaveProperty("name", "barcode");
    for (const char of "8901") {
        await advanceTime(20);
        await imeInput(char);
    }
    await advanceTime(40);
    expect.verifySteps([]);
    await advanceTime(20);
    expect.verifySteps(["8901"]);
});
