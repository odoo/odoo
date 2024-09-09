import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

import { ConvolutedElement, ConvolutedElementWithIframe } from "../src/convoluted_element";

/**
 * @hint `expect().toBeFocused()`
 * @hint `queryAllTexts()` ("@odoo/hoot-dom")
 * @hint selector with ":contains()"
 */
test.todo("convoluted element is rendered correctly", async () => {
    await mountWithCleanup(ConvolutedElement);

    expect(document.querySelector("input")).toBe(document.activeElement);
    expect(
        [...document.querySelectorAll("li")].map((listItem) => listItem.innerText.trim())
    ).toEqual(["Item 1", "Item 2", "Item 3"]);
    expect(
        [...document.querySelectorAll("li")].filter((listItem) =>
            listItem.innerText.includes("Item")
        )
    ).toHaveCount(3);
});

/**
 * @hint `expect().toHaveText()`
 * @hint selector with ":iframe"
 */
test.todo("convoluted element with iframe is rendered correctly", async () => {
    await mountWithCleanup(ConvolutedElementWithIframe);
    await animationFrame(); // wait for iframe

    expect(
        document.querySelector("iframe").contentDocument.querySelector("p").innerText.trim()
    ).toBe("Hello");
});
