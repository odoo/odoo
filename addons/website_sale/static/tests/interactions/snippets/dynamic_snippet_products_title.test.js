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
    await setupWebsiteBuilderWithSnippet("s_dynamic_snippet_products");
    expect(snippetSelector).toHaveCount(1);
    await clickAndWait(`${snippetSelector} .s_dynamic_snippet_title`);
    await clickAndWait(
        "[data-container-title='Block'] [data-label='Section Title'] button[data-action-param='left']"
    );
    const snippetEl = queryOne(snippetSelector);
    const snippetTitleEl = queryOne(`${snippetSelector} .s_dynamic_snippet_title`);
    expect(snippetEl.dataset.numberOfElements).toBe("2");
    expect(snippetTitleEl.classList.contains("s_dynamic_snippet_title_aside")).toBe(true);
});
