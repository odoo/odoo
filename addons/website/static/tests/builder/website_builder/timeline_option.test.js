import { expect, test } from "@odoo/hoot";
import { queryAll, queryAllTexts } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("add a date in timeline", async () => {
    await setupWebsiteBuilderWithSnippet("s_timeline");
    expect(queryAllTexts(":iframe .s_timeline_row h3")).toEqual([
        "First Feature",
        "Second Feature",
        "Third Feature",
        "Latest Feature",
    ]);
    await contains(":iframe .s_timeline").click();
    await contains("[data-action-id='addItem']").click();
    expect(queryAllTexts(":iframe .s_timeline_row h3")).toEqual([
        "First Feature",
        "First Feature",
        "Second Feature",
        "Third Feature",
        "Latest Feature",
    ]);
    const timelineRow = queryAll(":iframe .s_timeline_row");
    expect(timelineRow[0].textContent).toBe(timelineRow[1].textContent);
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
