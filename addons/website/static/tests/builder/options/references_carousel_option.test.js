import { expect, test } from "@odoo/hoot";
import { queryFirst } from "@odoo/hoot-dom";
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

    const cloneButtonSelector = "[data-container-title='Reference'] .oe_snippet_clone";
    const removeButtonSelector = "[data-container-title='Reference'] .oe_snippet_remove";
    await contains(cloneButtonSelector).click();
    expect(itemSelector).toHaveCount(7);

    // Remove references down to the last one, which cannot be removed.
    for (let i = 0; i < 6; i++) {
        await contains(removeButtonSelector).click();
    }
    expect(itemSelector).toHaveCount(1);
    expect(removeButtonSelector).toHaveAttribute("disabled");

    // Even when the user clicks fast on the remove button.
    await contains(cloneButtonSelector).click();
    expect(itemSelector).toHaveCount(2);
    expect(removeButtonSelector).not.toHaveAttribute("disabled");
    await contains(removeButtonSelector).dblclick();
    expect(itemSelector).toHaveCount(1);
    expect(removeButtonSelector).toHaveAttribute("disabled");
});

test("Add a reference from the snippet options", async () => {
    await setupWebsiteBuilderWithSnippet("s_references_carousel", { loadIframeBundles: true });
    const itemSelector = ":iframe .s_references_carousel .s_references_carousel_item";
    await contains(":iframe .s_references_carousel_title h2").click();
    await contains("[data-action-id='addItem']").click();
    expect(itemSelector).toHaveCount(7);
    // The new reference is selected, so that its logo can be replaced.
    expect("[data-container-title='Reference']").toHaveCount(1);
});

test("Title position", async () => {
    await setupWebsiteBuilderWithSnippet("s_references_carousel", { loadIframeBundles: true });
    const titleSelector = ":iframe .s_references_carousel_title";
    await contains(`${titleSelector} h2`).click();
    const buttonSelector = (label) => `[data-label='Title'] button:contains('${label}')`;

    await contains(buttonSelector("Left")).click();
    expect(titleSelector).toHaveClass("col-lg-3");
    expect(buttonSelector("Left")).toHaveClass("active");

    await contains(buttonSelector("None")).click();
    expect(titleSelector).toHaveClass("d-none");
    expect(titleSelector).not.toHaveClass("col-lg-3");

    await contains(buttonSelector("Top")).click();
    expect(titleSelector).not.toHaveClass("d-none");
    expect(buttonSelector("Top")).toHaveClass("active");
});

test("A logo is only edited through its reference", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilderWithSnippet("s_references_carousel", {
        loadIframeBundles: true,
    });
    // Images are loaded without source: give one a size so that it can be
    // clicked.
    queryFirst(":iframe .s_references_carousel_item img").style.cssText =
        "width: 100px; height: 50px;";
    await contains(":iframe .s_references_carousel_item img:first").click();
    await waitSidebarUpdated();
    const labelSelector = (title) =>
        `[data-container-title='${title}'] .o_hb_options_container_label`;
    // Clicking a logo unfolds the options of its reference too.
    expect(labelSelector("Image")).toHaveAttribute("aria-expanded", "true");
    expect(labelSelector("Reference")).toHaveAttribute("aria-expanded", "true");
    // On its own, a duplicated logo would share its cell, and the last one
    // removed would leave an empty strip.
    expect("[data-container-title='Image'] .oe_snippet_clone").toHaveCount(0);
    expect("[data-container-title='Image'] .oe_snippet_remove").toHaveCount(0);
});

test("A logo has no image size option", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilderWithSnippet("s_references_carousel", {
        loadIframeBundles: true,
    });
    queryFirst(":iframe .s_references_carousel_item img").style.cssText =
        "width: 100px; height: 50px;";
    await contains(":iframe .s_references_carousel_item img:first").click();
    await waitSidebarUpdated();
    // Sized by the "Logo Size" option of the snippet instead.
    expect("[data-container-title='Image'] [data-label='Transform']").toHaveCount(1);
    expect("[data-container-title='Image'] [data-label='Size']").toHaveCount(0);
});
