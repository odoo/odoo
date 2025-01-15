import { expect, test } from "@odoo/hoot";
import { queryAll, queryAllTexts } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "../helpers";
import { insertStructureSnippet } from "./helpers";

defineWebsiteModels();

test("add a date in timeline", async () => {
    const { getEditor } = await setupWebsiteBuilder("<div></div>");
    const editor = getEditor();
    await insertStructureSnippet(editor, "s_timeline");
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
