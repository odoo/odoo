/** @odoo-module **/

import { beforeEach, expect, test } from "@odoo/hoot";
import { barcodeService } from "@barcodes/barcode_service";
import { contains, mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { Component, xml } from "@odoo/owl";
import { click, press } from "@odoo/hoot-dom";

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
    await press("a");
    //hidden barcode input should have the focus
    expect(document.activeElement.name).toEqual("barcode");

    await contains("select").click();
    await press("b");

    //hidden barcode input should have the focus
    expect(document.activeElement.name).toEqual("barcode");

    // Those elements absolutely need to keep the focus:
    // inputs elements:
    for (const inputName of ["email", "number", "password", "tel", "text", "explicit_text"]) {
        const selector = `input[name="${inputName}"]`;
        await contains(selector).click();
        await press("c");
        // input selector should keep focus
        expect(selector).toBeFocused();
    }

    // textarea element
    await contains("textarea").click();
    await press("d");
    expect("textarea").toBeFocused();

    // contenteditable elements
    await contains("[contenteditable=true]").click();
    await press("e");
    //contenteditable should keep focus
    expect("[contenteditable=true]").toBeFocused();
});
