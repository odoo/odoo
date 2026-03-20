/** @odoo-module **/

import { beforeEach, expect, test } from "@odoo/hoot";
import { getActiveElement, queryFirst, keyDown, click } from "@odoo/hoot-dom";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
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
