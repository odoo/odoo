import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";
import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";

defineWebsiteModels();

test("Last floating blocks card cannot be removed", async () => {
    await setupWebsiteBuilderWithSnippet("s_floating_blocks");
    expect(":iframe .s_floating_blocks_block").toHaveCount(3);
    await contains(":iframe .s_floating_blocks_block").click();

    const removeSelector = "[data-container-title='Card'] .oe_snippet_remove";
    // A card is removable as long as it is not the last one.
    expect(removeSelector).not.toHaveAttribute("disabled");
    await contains(removeSelector).click();
    await contains(removeSelector).click();

    // The last card cannot be removed.
    expect(":iframe .s_floating_blocks_block").toHaveCount(1);
    expect(removeSelector).toHaveAttribute("disabled");
});
