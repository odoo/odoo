import { expect, test } from "@odoo/hoot";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";
import { contains } from "@web/../tests/web_test_helpers";

defineWebsiteModels();

test("Add/remove references", async () => {
    // The snippet stylesheet gives the logo cells their size (images are
    // loaded without source), so that they can be clicked.
    await setupWebsiteBuilderWithSnippet("s_references_carousel", { loadIframeBundles: true });
    const itemSelector = ":iframe .s_references_carousel .s_references_carousel_item";
    await contains(`${itemSelector}:first`).click();
    expect(itemSelector).toHaveCount(6);

    // Add a reference.
    const addButtonSelector =
        "[data-container-title='Reference'] button[aria-label='Add Reference']";
    const removeButtonSelector =
        "[data-container-title='Reference'] button[aria-label='Remove Reference']";
    await contains(addButtonSelector).click();
    expect(itemSelector).toHaveCount(7);

    // Remove references down to the last one, which cannot be removed.
    for (let i = 0; i < 6; i++) {
        await contains(removeButtonSelector).click();
    }
    expect(itemSelector).toHaveCount(1);
    expect(removeButtonSelector).toHaveAttribute("disabled");

    // Check that the last reference is never removed, even if the user clicks
    // fast on the "remove" button. For this test, we simulate a double click
    // when only two references are present.
    await contains(addButtonSelector).click();
    expect(itemSelector).toHaveCount(2);
    expect(removeButtonSelector).not.toHaveAttribute("disabled");
    await contains(removeButtonSelector).dblclick();
    expect(itemSelector).toHaveCount(1);
    expect(removeButtonSelector).toHaveAttribute("disabled");
});
