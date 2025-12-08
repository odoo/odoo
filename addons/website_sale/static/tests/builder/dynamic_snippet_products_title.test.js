import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";
import { defineModels, fields, models, onRpc } from "@web/../tests/web_test_helpers";
import { animationFrame, click, queryOne } from "@odoo/hoot-dom";
import { expect, test } from "@odoo/hoot";

class ProductPublicCategory extends models.Model {
    name = fields.Char({ string: "Category name" });
    _records = [{ id: 1, name: "All Products" }];
}

defineWebsiteModels();
defineModels([ProductPublicCategory]);

async function clickAndWait(selector) {
    await click(selector);
    await animationFrame();
}

async function checkNumberOfElements(actionParam, dataLabel, expectedValue, snippetEl) {
    await clickAndWait(
        `[data-container-title='Products'] [data-label='${dataLabel}'] button[data-action-param='${actionParam}']`
    );
    expect(snippetEl.dataset.numberOfElements).toBe(String(expectedValue));
}

test("for dynamic snippet products, the numberOfElements should be 2 when title is on left", async () => {
    onRpc("/website/snippet/options_filters", async () => [
        {
            id: 1,
            name: "Featured Products",
            limit: 10,
            model_name: "product.product",
            help: "Show featured products",
        },
    ]);

    onRpc("/website/snippet/filter_templates", async () => [
        {
            key: "website_sale.dynamic_filter_template_product_product_products_item",
            name: "Product Item Template",
            numOfEl: "4",
        },
    ]);

    const snippetSelector = ":iframe .s_dynamic_snippet_products";
    const { getEditableContent } = await setupWebsiteBuilderWithSnippet(
        "s_dynamic_snippet_products"
    );
    expect(snippetSelector).toHaveCount(1);
    await clickAndWait(snippetSelector);
    const snippetEl = queryOne(snippetSelector);
    await checkNumberOfElements("left", "Section Title", 2, snippetEl);
    await checkNumberOfElements("container-fluid", "Content Width", 4, snippetEl);
    const carouselEl = getEditableContent().querySelector(".carousel");
    carouselEl.addEventListener("content_changed", () => {
        expect.step("content_changed event received");
    });
    await checkNumberOfElements("o_container_small", "Content Width", 2, snippetEl);
    // Just to ensure that the event is triggerd on option change.
    expect.verifySteps(["content_changed event received", "content_changed event received"]); // preview, apply
});
