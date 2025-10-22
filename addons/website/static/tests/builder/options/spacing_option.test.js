import { expect, test } from "@odoo/hoot";
import { edit, manuallyDispatchProgrammaticEvent, queryOne } from "@odoo/hoot-dom";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("Use the 'Spacing (Y, X)' option", async () => {
    await setupWebsiteBuilderWithSnippet("s_banner", { loadIframeBundles: true });
    await contains(":iframe .s_banner").click();
    expect(":iframe .s_banner .row").toHaveStyle({ "row-gap": "0px" });
    expect(":iframe .s_banner .row").toHaveStyle({ "column-gap": "0px" });

    await contains("[data-label='Spacing (Y, X)'] [data-action-param='row-gap'] input").edit(10);
    expect(":iframe .s_banner .row").toHaveStyle({ "row-gap": "10px" });
    expect(":iframe .s_banner .row").toHaveStyle({ "column-gap": "0px" });

    await contains("[data-label='Spacing (Y, X)'] [data-action-param='column-gap'] input").edit(20);
    expect(":iframe .s_banner .row").toHaveStyle({ "row-gap": "10px" });
    expect(":iframe .s_banner .row").toHaveStyle({ "column-gap": "20px" });
});

test("Using the 'Spacing (Y, X)' option should display a grid preview", async () => {
    await setupWebsiteBuilderWithSnippet("s_banner", { loadIframeBundles: true });
    await contains(":iframe .s_banner").click();
    await contains("[data-label='Spacing (Y, X)'] input").click();
    await edit(20);
    expect(":iframe .o_we_grid_preview").toHaveCount(1);

    const cell = queryOne(":iframe .o_we_grid_preview .o_we_cell");
    expect(cell).toHaveStyle({
        "animation-name": "gridPreview",
    });
    // 'animationend' event is manually dispatched to speed up the test since the
    // actual animation takes 2 seconds.
    await manuallyDispatchProgrammaticEvent(cell, "animationend");

    expect(":iframe .o_we_grid_preview").toHaveCount(0);
});

test("Cloning a block with a grid preview should not make the preview appear on the clone", async () => {
    await setupWebsiteBuilderWithSnippet("s_banner", { loadIframeBundles: true });
    await contains(":iframe .s_banner").click();
    expect(":iframe .s_banner").toHaveCount(1);
    await contains("[data-label='Spacing (Y, X)'] input").click();
    await edit(20);
    await contains("[data-container-title='Block'] .oe_snippet_clone").click();
    expect(":iframe .s_banner").toHaveCount(2);
    expect(":iframe .s_banner:nth-child(1) .o_we_grid_preview").toHaveCount(1);
    expect(":iframe .s_banner:nth-child(2) .o_we_grid_preview").toHaveCount(0);
});

test("Saving a block with a grid preview should not save the preview", async () => {
    const saveResult = [];
    onRpc("ir.ui.view", "save", ({ args }) => {
        saveResult.push(args[1]);
        return true;
    });
    await setupWebsiteBuilderWithSnippet("s_banner", { loadIframeBundles: true });
    await contains(":iframe .s_banner").click();
    expect(":iframe .s_banner").toHaveCount(1);
    await contains("[data-label='Spacing (Y, X)'] input").click();
    await edit(20);

    await contains(".o-snippets-top-actions [data-action='save']").click();
    expect(saveResult[0].includes("o_we_grid_preview")).toBe(false);
});
