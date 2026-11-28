import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";
import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";

defineWebsiteModels();

/**
 * Checks one group of rating icons: how many there are, their icon and whether
 * they are filled. An empty group only has its count checked.
 *
 * @param {"active"|"inactive"} group
 * @param {number} count
 * @param {{ icon: string, filled: boolean }} [iconSpec]
 */
function expectIcons(group, count, { icon, filled } = {}) {
    const iconSelector = `:iframe .s_rating_${group}_icons i`;
    expect(iconSelector).toHaveCount(count);
    if (count) {
        expect(iconSelector).toHaveAttribute("data-icon", icon);
        expect(`${iconSelector}${filled ? ".oi-filled" : ":not(.oi-filled)"}`).toHaveCount(count);
    }
}

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

test("standard icons are preserved after score change", async () => {
    await setupWebsiteBuilderWithSnippet("s_rating", { loadIframeBundles: true });
    await contains(":iframe .s_rating").click();

    await contains("[data-action-id='activeIconsNumber'] input").edit("2");
    expect(":iframe .s_rating_icons i").toHaveAttribute("data-icon", "star");
});

test("custom icons keep their icon and fill when the score changes", async () => {
    await setupWebsiteBuilderWithSnippet("s_rating", { loadIframeBundles: true });
    await contains(":iframe .s_rating").click();

    await contains("[data-action-id='customIcon'][data-action-param='customActiveIcon']").click();
    await contains(".o_select_media_dialog span[data-icon='favorite']:not(.oi-filled)").click();
    expectIcons("inactive", 2, { icon: "star", filled: true });
    await contains("[data-action-id='customIcon'][data-action-param='customInactiveIcon']").click();
    await contains(".o_select_media_dialog span.oi-filled[data-icon='favorite']").click();
    expectIcons("active", 3, { icon: "favorite", filled: false });
    expectIcons("inactive", 2, { icon: "favorite", filled: true });

    await contains("[data-action-id='activeIconsNumber'] input").edit("5");
    expectIcons("active", 5, { icon: "favorite", filled: false });
    expectIcons("inactive", 0);

    // The inactive icons come back from an empty group.
    await contains("[data-action-id='activeIconsNumber'] input").edit("2");
    expectIcons("active", 2, { icon: "favorite", filled: false });
    expectIcons("inactive", 3, { icon: "favorite", filled: true });

    // A standard icon set drops the picked fills.
    await contains("[data-label='Icon'] .dropdown-toggle").click();
    await contains("[data-action-id='setIcons'][data-action-param='star']").click();
    expectIcons("active", 2, { icon: "star", filled: true });
    expectIcons("inactive", 3, { icon: "star", filled: false });
});
