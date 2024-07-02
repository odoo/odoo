import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

import { ConvolutedElement, ConvolutedElementWithIframe } from "../src/convoluted_element";

/**
 * @hint `expect().toBeFocused()`
 * @hint `queryAllTexts()` ("@odoo/hoot-dom")
 * @hint selector with ":contains()"
 */
test("convoluted element is rendered correctly", async () => {
    await mountWithCleanup(ConvolutedElement);

    expect("input").toBeFocused();
    expect(queryAllTexts("li")).toEqual(["Item 1", "Item 2", "Item 3"]);
    expect("li:contains(Item)").toHaveCount(3);
});

/**
 * @hint `expect().toHaveText()`
 * @hint selector with ":iframe"
 */
test("convoluted element with iframe is rendered correctly", async () => {
    await mountWithCleanup(ConvolutedElementWithIframe);
    await animationFrame(); // wait for iframe

    expect(":iframe p").toHaveText("Hello");
});
