import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";
import { animationFrame, expect, test, press } from "@odoo/hoot";
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

test("clicking on a rating icon updates score and aria-label", async () => {
    await setupWebsiteBuilderWithSnippet("s_rating", { loadIframeBundles: true });

    await contains(":iframe .s_rating_icons i:nth-child(3)").click();
    await animationFrame();

    expect(":iframe .s_rating_icons").toHaveAttribute("aria-label", "3 out of 5 stars");
    expect(":iframe .s_rating_icons i.oi-filled").toHaveCount(3);
    expect(":iframe .s_rating_icons i:not(.oi-filled)").toHaveCount(2);

    await contains(":iframe .s_rating_icons i:nth-child(1)").click();
    await animationFrame();
    expect(":iframe .s_rating_icons").toHaveAttribute("aria-label", "1 out of 5 stars");
    expect(":iframe .s_rating_icons i.oi-filled").toHaveCount(1);
    expect(":iframe .s_rating_icons i:not(.oi-filled)").toHaveCount(4);

    expect("[data-action-id='activeIconsNumber'] input").toHaveValue(1);

    await press(["control", "z"]);
    await animationFrame();

    expect(":iframe .s_rating_icons").toHaveAttribute("aria-label", "3 out of 5 stars");
    expect(":iframe .s_rating_icons i.oi-filled").toHaveCount(3);

    await press(["control", "y"]);
    await animationFrame();

    expect(":iframe .s_rating_icons").toHaveAttribute("aria-label", "1 out of 5 stars");
    expect(":iframe .s_rating_icons i.oi-filled").toHaveCount(1);
});
