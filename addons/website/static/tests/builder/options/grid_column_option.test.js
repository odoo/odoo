import { expect, test } from "@odoo/hoot";
import {
    animationFrame,
    click,
    Deferred,
    edit,
    queryAll,
    queryFirst,
    waitFor,
} from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("Using the Padding (Y, X) option should display a padding preview", async () => {
    await setupWebsiteBuilderWithSnippet("s_banner", { loadIframeBundles: true });
    await contains(":iframe .s_banner .o_grid_item").click();
    await waitFor("[data-label='Padding (Y, X)'] input");
    await click(queryAll("[data-label='Padding (Y, X)'] input")[0]);
    await edit(20);
    const def = new Deferred();
    expect(queryFirst(":iframe .s_banner .o_grid_item")).toHaveClass("o_we_padding_highlight");
    queryFirst(":iframe .s_banner .o_grid_item").addEventListener("animationend", () => {
        def.resolve();
    });
    await def;
    await animationFrame();
    expect(queryFirst(":iframe .s_banner .o_grid_item")).not.toHaveClass("o_we_padding_highlight");
});

test("Cloning a block with a padding preview should not make the preview appear on the clone", async () => {
    await setupWebsiteBuilderWithSnippet("s_banner", { loadIframeBundles: true });
    await contains(":iframe .s_banner .o_grid_item").click();
    await waitFor("[data-label='Padding (Y, X)'] input");
    await click(queryAll("[data-label='Padding (Y, X)'] input")[0]);
    expect(":iframe .s_banner .o_grid_item").toHaveCount(4);
    await edit(20);
    await click("[data-container-title='Box'] .oe_snippet_clone");
    await animationFrame();
    expect(":iframe .s_banner .o_grid_item").toHaveCount(5);
    expect(":iframe .s_banner .o_grid_item:nth-child(1)").toHaveClass("o_we_padding_highlight");
    expect(":iframe .s_banner .o_grid_item:nth-child(2)").not.toHaveClass("o_we_padding_highlight");
});
