import { expect, test } from "@odoo/hoot";
import { queryOne, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("masonry image blocks can't be made clickable", async () => {
    await setupWebsiteBuilderWithSnippet("s_masonry_block", { loadIframeBundles: true });
    await contains(":iframe .s_masonry_block .o_grid_item_image").click();
    await waitFor("[data-container-title='Block']");
    expect("[data-action-id='setElementClickable']").toHaveCount(0);
});

test("make a masonry block clickable", async () => {
    await setupWebsiteBuilderWithSnippet("s_masonry_block", { loadIframeBundles: true });
    const blockSelector = ":iframe .s_masonry_block .o_grid_item:last-child";
    await contains(blockSelector).click();
    await contains("[data-action-id='setElementClickable'] input").click();
    await contains("[data-action-id='setElementAnchorUrl'] input").edit("https://www.example.com", {
        confirm: "blur",
    });
    const linkEl = queryOne(`${blockSelector} > a.stretched-link`);
    expect(linkEl).toHaveAttribute("href", "https://www.example.com");
    expect(linkEl.offsetParent).toBe(queryOne(blockSelector));
});
