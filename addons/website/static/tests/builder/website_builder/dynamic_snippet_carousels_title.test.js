import { expect, test } from "@odoo/hoot";
import { animationFrame, click, queryOne } from "@odoo/hoot-dom";
import { onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";
import {
    DEFAULT_NUMBER_OF_ELEMENTS,
    DEFAULT_NUMBER_OF_ELEMENTS_FOR_TITLE_LEFT,
} from "@website/utils/constants";

defineWebsiteModels();

async function checkNumberOfElements(actionParam, dataLabel, expectedValue, snippetEl) {
    await click(
        `[data-container-title='Dynamic Carousel'] [data-label='${dataLabel}'] button[data-action-param*='${actionParam}']`
    );
    await animationFrame();
    expect(snippetEl.dataset.numberOfElements).toBe(String(expectedValue));
}

test("dynamic snippet carousels: adjusts numberOfElements based on title position and content width", async () => {
    onRpc("/website/snippet/options_filters", async () => [
        {
            id: 1,
            name: "Carousel Items",
            limit: 10,
            model_name: "base",
            help: "Show carousel items",
        },
    ]);

    onRpc("/website/snippet/filter_templates", async () => [
        {
            key: "website.dynamic_filter_template_base_carousel_item",
            name: "Carousel Item Template",
            numberOfElements: "4",
        },
    ]);
    const snippetSelector = ":iframe .s_dynamic_snippet_carousel";
    await setupWebsiteBuilderWithSnippet("s_dynamic_snippet_carousel");
    expect(`${snippetSelector}.o_dynamic_snippet_carousel`).toHaveCount(1);
    const snippetEl = queryOne(snippetSelector);
    snippetEl.dataset.filterId = "1";
    await click(snippetSelector);
    await animationFrame();
    await checkNumberOfElements(
        "s_dynamic_snippet_title_aside",
        "Section Title",
        DEFAULT_NUMBER_OF_ELEMENTS_FOR_TITLE_LEFT,
        snippetEl
    );
    await checkNumberOfElements(
        "container-fluid",
        "Content Width",
        DEFAULT_NUMBER_OF_ELEMENTS,
        snippetEl
    );
    await checkNumberOfElements(
        "o_container_small",
        "Content Width",
        DEFAULT_NUMBER_OF_ELEMENTS_FOR_TITLE_LEFT,
        snippetEl
    );
});
