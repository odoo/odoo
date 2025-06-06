import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilderWithSnippet } from "../website_helpers";
import { waitFor } from "@odoo/hoot-dom";

defineWebsiteModels();

test("Reordering a carousel item should update the container title", async () => {
    const { getEditor, getEditableContent } = await setupWebsiteBuilderWithSnippet("s_carousel");
    // Add a class on the first slide to identify it.
    const editableEl = getEditableContent();
    const firstItemEl = editableEl.querySelector(".carousel-item");
    firstItemEl.classList.add("first-slide");

    const editor = getEditor();
    const builderOptions = editor.shared["builder-options"];
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
