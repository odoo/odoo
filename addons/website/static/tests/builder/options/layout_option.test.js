import { expect, test } from "@odoo/hoot";
import { animationFrame, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("switch grid layout to column layout", async () => {
    await setupWebsiteBuilderWithSnippet("s_banner");
    await contains(":iframe .s_banner").click();
    await waitFor("[data-action-id='setGridLayout']");
    expect("[data-action-id='setGridLayout']").toHaveClass("active");
    expect("[data-action-id='setColumnLayout']").not.toHaveClass("active");
    expect("[data-label='Layout'] .dropdown-toggle").not.toHaveCount();

    await contains("[data-action-id='setColumnLayout']").click();
    expect("[data-action-id='setGridLayout']").not.toHaveClass("active");
    expect("[data-action-id='setColumnLayout']").toHaveClass("active");
    expect("[data-label='Layout'] .dropdown-toggle").toBeVisible();
    expect("[data-label='Layout'] .dropdown-toggle").toHaveText("Custom");

    await contains("[data-label='Layout'] .dropdown-toggle").click();
    await contains("[data-action-value='5']").click();
    expect("[data-label='Layout'] .dropdown-toggle").toHaveText("5");
});

test("switch to mobile mode should update number of columns", async () => {
    await setupWebsiteBuilderWithSnippet("s_three_columns");
    await contains(":iframe .s_three_columns").click();
    await waitFor("[data-action-id='setGridLayout']");
    expect("[data-action-id='setGridLayout']").not.toHaveClass("active");
    expect("[data-action-id='setColumnLayout']").toHaveClass("active");
    expect("[data-label='Layout'] .dropdown-toggle").toBeVisible();
    expect("[data-label='Layout'] .dropdown-toggle").toHaveText("3");

    await contains("button[data-action='mobile']").click();
    expect("[data-label='Layout'] .dropdown-toggle").toHaveText("1");
});

test("Changing the number of columns to 'None' (0)", async () => {
    await setupWebsiteBuilderWithSnippet(["s_text_image", "s_text_block"]);
    await contains(":iframe .s_text_image").click();
    await contains("[data-label='Layout'] .dropdown").click();
    expect("[data-action-id='changeColumnCount'][data-action-value='0']").toHaveCount(0);

    await contains(":iframe .s_text_block").click();
    expect(":iframe .s_text_block .row").toHaveCount(0);
    await animationFrame();
    expect("[data-label='Layout'] .dropdown:contains(None)").toHaveCount(1);

    await contains("[data-label='Layout'] .dropdown").click();
    await contains("[data-action-id='changeColumnCount'][data-action-value='1']").click();
    expect(":iframe .s_text_block .container > .row:only-child > .col-lg-12").toHaveCount(1);

    await contains("[data-label='Layout'] .dropdown").click();
    await contains("[data-action-id='changeColumnCount'][data-action-value='0']").click();
    expect(":iframe .s_text_block .row").toHaveCount(0);
});

test("Adding columns does not introduce extra offset (offset class removed on clone)", async () => {
    await setupWebsiteBuilderWithSnippet(["s_text_block"]);
    await contains(":iframe .s_text_block").click();
    await contains("[data-label='Layout'] .dropdown").click();
    await contains("[data-action-id='changeColumnCount'][data-action-value='5']").click();
    expect(":iframe .s_text_block .container > .row > .offset-lg-1").toHaveCount(1);
});
