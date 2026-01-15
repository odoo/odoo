import { expect, test } from "@odoo/hoot";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";
import { contains } from "@web/../tests/web_test_helpers";
import { animationFrame, setInputRange } from "@odoo/hoot-dom";

defineWebsiteModels();

test("Change carousel speed", async () => {
    await setupWebsiteBuilderWithSnippet("s_references_carousel", { loadIframeBundles: true });
    await contains(":iframe .s_references_carousel_slider").click();
    expect(".options-container[data-container-title='References Carousel']").toHaveCount(1);
    expect("[data-label='Speed'] input").toHaveValue(5);
    expect(":iframe .s_references_carousel_slider").toHaveStyle("--speed: 5s");

    await setInputRange("[data-label='Speed'] input", 8);
    await animationFrame();
    expect(":iframe .s_references_carousel_slider").toHaveStyle("--speed: 8s");
});

test("Add/remove carousel items", async () => {
    await setupWebsiteBuilderWithSnippet("s_references_carousel");
    await contains(":iframe .s_references_carousel_slider").click();
    expect(":iframe .s_references_carousel_item").toHaveCount(7);

    // Remove an item.
    const removeButtonSelector =
        "[data-container-title='Slider'] button[aria-label='Remove Reference']";
    await contains(removeButtonSelector).click();
    expect(":iframe .s_references_carousel_item").toHaveCount(6);

    // Verify positions are updated correctly.
    expect(":iframe .s_references_carousel_item:nth-child(1)").toHaveStyle("--position: 1");
    expect(":iframe .s_references_carousel_item:nth-child(6)").toHaveStyle("--position: 6");

    // Remove items until only one remains.
    await contains(removeButtonSelector).click();
    await contains(removeButtonSelector).click();
    await contains(removeButtonSelector).click();
    await contains(removeButtonSelector).click();
    await contains(removeButtonSelector).click();

    expect(":iframe .s_references_carousel_item").toHaveCount(1);

    // Check that we cannot remove anymore with only one item remaining.
    expect(removeButtonSelector).toHaveAttribute("disabled");

    // Add an item.
    const addButtonSelector = "[data-container-title='Slider'] button[aria-label='Add Reference']";
    await contains(addButtonSelector).click();
    expect(":iframe .s_references_carousel_item").toHaveCount(2);
    expect(":iframe .s_references_carousel_item:nth-child(1)").toHaveStyle("--position: 1");
    expect(":iframe .s_references_carousel_item:nth-child(2)").toHaveStyle("--position: 2");
    expect(removeButtonSelector).not.toHaveAttribute("disabled");

    // Add multiple items.
    await contains(addButtonSelector).click();
    await contains(addButtonSelector).click();
    expect(":iframe .s_references_carousel_item").toHaveCount(4);
});
