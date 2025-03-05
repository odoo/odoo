import { expect, test } from "@odoo/hoot";
import { queryAll } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilderWithSnippet } from "../website_helpers";

defineWebsiteModels();

test("switch grid layout to column layout", async () => {
    await setupWebsiteBuilderWithSnippet("s_banner");
    await contains(":iframe .s_banner").click();
    expect("[data-action-id='setGridLayout']").toHaveClass("active");
    expect("[data-action-id='setColumnLayout']").not.toHaveClass("active");
    expect("[data-label='Layout'] .dropdown-toggle").not.toBeVisible();

    await contains("[data-action-id='setColumnLayout']").click();
    expect("[data-action-id='setGridLayout']").not.toHaveClass("active");
    expect("[data-action-id='setColumnLayout']").toHaveClass("active");
    expect("[data-label='Layout'] .dropdown-toggle").toBeVisible();
    expect("[data-label='Layout'] .dropdown-toggle").toHaveText("Custom");

    await contains("[data-label='Layout'] .dropdown-toggle").click();
    await contains("[data-action-value='5']").click();
    expect("[data-label='Layout'] .dropdown-toggle").toHaveText("5");
});

test("edit section spacing (Y,X)", async () => {
    await setupWebsiteBuilderWithSnippet("s_banner");
    await contains(":iframe .s_banner").click();
    expect(":iframe .s_banner .row").toHaveStyle({ "row-gap": "normal" });
    expect(":iframe .s_banner .row").toHaveStyle({ "column-gap": "normal" });

    await contains("[data-label='Spacing (Y, X)'] input:first").edit(10);
    expect(":iframe .s_banner .row").toHaveStyle({ "row-gap": "10px" });
    expect(":iframe .s_banner .row").toHaveStyle({ "column-gap": "normal" });

    await contains(queryAll("[data-label='Spacing (Y, X)'] input")[1]).edit(20);
    expect(":iframe .s_banner .row").toHaveStyle({ "row-gap": "10px" });
    expect(":iframe .s_banner .row").toHaveStyle({ "column-gap": "20px" });
});

test("switch to mobile mode should update number of columns", async () => {
    await setupWebsiteBuilderWithSnippet("s_three_columns");
    await contains(":iframe .s_three_columns").click();
    expect("[data-action-id='setGridLayout']").not.toHaveClass("active");
    expect("[data-action-id='setColumnLayout']").toHaveClass("active");
    expect("[data-label='Layout'] .dropdown-toggle").toBeVisible();
    expect("[data-label='Layout'] .dropdown-toggle").toHaveText("3");

    await contains("button[data-action='mobile']").click();
    expect("[data-label='Layout'] .dropdown-toggle").toHaveText("1");
});
