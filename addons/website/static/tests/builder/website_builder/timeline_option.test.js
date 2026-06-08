import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("add milestones in timeline", async () => {
    await setupWebsiteBuilderWithSnippet("s_timeline");
    expect(queryAllTexts(":iframe .s_timeline_row h3")).toEqual([
        "First Feature",
        "Second Feature",
        "Third Feature",
        "Latest Feature",
    ]);
    await contains(":iframe .s_timeline").click();
    await contains("[data-action-id='addMilestone'][data-action-value='left']").click();
    expect(queryAllTexts(":iframe .s_timeline_row h3")).toEqual([
        "First Feature",
        "Second Feature",
        "Third Feature",
        "Latest Feature",
        "Next Feature",
    ]);
    await contains("[data-action-id='addMilestone'][data-action-value='right']").click();
    expect(queryAllTexts(":iframe .s_timeline_row h3")).toEqual([
        "First Feature",
        "Second Feature",
        "Third Feature",
        "Latest Feature",
        "Next Feature",
        "Latest Feature",
    ]);
    await contains("[data-action-id='addMilestone'][data-action-value='both']").click();
    expect(queryAllTexts(":iframe .s_timeline_row h3")).toEqual([
        "First Feature",
        "Second Feature",
        "Third Feature",
        "Latest Feature",
        "Next Feature",
        "Latest Feature",
        "Next Feature",
        "Latest Feature",
    ]);
});

test("Use the overlay buttons of a timeline card", async () => {
    await setupWebsiteBuilderWithSnippet("s_timeline");
    await contains(":iframe .s_timeline_card").click();
    expect(".o_overlay_options .fa-angle-right").toHaveCount(1);
    expect(".o_overlay_options .fa-angle-left").toHaveCount(0);

    await contains(".o_overlay_options .fa-angle-right").click();
    expect(".o_overlay_options .fa-angle-right").toHaveCount(0);
    expect(".o_overlay_options .fa-angle-left").toHaveCount(1);
});

test("last timeline element cannot be removed", async () => {
    await setupWebsiteBuilderWithSnippet("s_timeline");
    await contains(":iframe .s_timeline_row").click();

    // The first row (Milestone) of a fresh snippet is removable.
    expect("[data-container-title='Milestone'] .oe_snippet_remove").not.toHaveAttribute("disabled");

    // Remove rows until only one row remains.
    await contains("[data-container-title='Milestone'] .oe_snippet_remove").click();
    await contains("[data-container-title='Milestone'] .oe_snippet_remove").click();

    // The last row cannot be removed.
    expect("[data-container-title='Milestone'] .oe_snippet_remove").toHaveAttribute("disabled");
    // The last card (Milestone Event) cannot be removed.
    await contains(":iframe .s_timeline_card").click();
    expect("[data-container-title='Milestone Event'] .oe_snippet_remove").toHaveAttribute(
        "disabled"
    );
});

test("Auto remove empty rows in timeline", async () => {
    await setupWebsiteBuilderWithSnippet("s_timeline");
    expect(":iframe .s_timeline_row").toHaveCount(3);
    // Removing only element i.e. card from a row should delete that row from snippet.
    await contains(":iframe .s_timeline_card").click();
    await contains(".overlay .oe_snippet_remove").click();
    expect(":iframe .s_timeline_row").toHaveCount(2);
});
