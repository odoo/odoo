import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";
import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";

defineWebsiteModels();

test("rating snippet should not be user-selectable", async () => {
    await setupWebsiteBuilderWithSnippet("s_rating", { loadIframeBundles: true });
    expect(":iframe .s_rating").toHaveStyle({ "user-select": "none" });
});

test("changing score should update the aria-label", async () => {
    await setupWebsiteBuilderWithSnippet("s_rating", { loadIframeBundles: true });

    await contains(":iframe .s_rating").click();

    await contains("[data-action-id='activeIconsNumber'] input").clear();
    await contains("[data-action-id='activeIconsNumber'] input").fill("2");

    expect(":iframe .s_rating_icons").toHaveAttribute("aria-label", "2 out of 5 stars");

    await contains("[data-action-id='activeIconsNumber'] input").clear();
    await contains("[data-action-id='activeIconsNumber'] input").fill("1");
    await contains("[data-action-id='totalIconsNumber'] input").clear();
    await contains("[data-action-id='totalIconsNumber'] input").fill("0");

    expect(":iframe .s_rating_icons").toHaveAttribute("aria-label", "1 out of 10 stars");
});
