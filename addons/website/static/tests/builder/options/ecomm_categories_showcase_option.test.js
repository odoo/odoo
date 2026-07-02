import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("Last ecomm categories showcase block cannot be removed", async () => {
    await setupWebsiteBuilderWithSnippet("s_ecomm_categories_showcase");
    expect(":iframe .s_ecomm_categories_showcase_block").toHaveCount(4);
    await contains(":iframe .s_ecomm_categories_showcase_block").click();

    const removeSelector = "[data-container-title='Category'] .oe_snippet_remove";
    // A block is removable as long as it is not the last one.
    expect(removeSelector).not.toHaveAttribute("disabled");
    await contains(removeSelector).click();
    await contains(removeSelector).click();
    await contains(removeSelector).click();

    // The last block cannot be removed.
    expect(":iframe .s_ecomm_categories_showcase_block").toHaveCount(1);
    expect(removeSelector).toHaveAttribute("disabled");
});
