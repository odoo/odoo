import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";
import { waitFor } from "@odoo/hoot-dom";

defineWebsiteModels();

test("Reordering a carousel item should update the container title", async () => {
    const { getEditor, getEditableContent } = await setupWebsiteBuilderWithSnippet("s_carousel");
    // Add a class on the first slide to identify it.
    const editableEl = getEditableContent();
    const firstItemEl = editableEl.querySelector(".carousel-item");
    firstItemEl.classList.add("first-slide");

    const editor = getEditor();
    const builderOptions = editor.shared.builderOptions;
    const expectOptionContainerToInclude = (elem) => {
        expect(builderOptions.getContainers().map((container) => container.element)).toInclude(
            elem
        );
    };

    await contains(":iframe .first-slide").click();
    await waitFor("[data-action-value='next']");
    expect("[data-container-title='Slide (1/3)']").toHaveCount(1);
    await contains("[data-action-value='next']").click();
    expectOptionContainerToInclude(firstItemEl);
    expect("[data-container-title='Slide (2/3)']").toHaveCount(1);
    await contains("[data-action-value='next']").click();
    expectOptionContainerToInclude(firstItemEl);
    expect("[data-container-title='Slide (3/3)']").toHaveCount(1);
});

test("Remove slide", async () => {
    await setupWebsiteBuilderWithSnippet("s_carousel");

    expect(":iframe .carousel-item").toHaveCount(3);
    await contains(":iframe .carousel-item").click();

    const removeSlideButton = await waitFor("button[title='Remove Slide']");
    removeSlideButton.click();
    removeSlideButton.click();
    await waitFor("[data-container-title='Slide (2/2)']", {
        message:
            "Clicking on Remove slide twice without waiting should not crash " +
            "and remove only one slide. Then it should focus on the previous slide.",
    });

    expect(":iframe .carousel-item").toHaveCount(2);
    expect(":iframe .carousel-item.active").toHaveCount(1);

    expect(":iframe .carousel-indicators > *").toHaveCount(2);
    expect(":iframe .carousel-indicators > .active").toHaveCount(1);
});
