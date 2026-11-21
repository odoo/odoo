import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";
import { redo, undo } from "@html_editor/../tests/_helpers/user_actions";
import { animationFrame, expect, test } from "@odoo/hoot";
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

test("changing the score keeps active icons filled and inactive ones hollow", async () => {
    await setupWebsiteBuilderWithSnippet("s_rating", { loadIframeBundles: true });
    expectIcons("active", 3, { icon: "star", filled: true });
    expectIcons("inactive", 2, { icon: "star", filled: false });

    await contains(":iframe .s_rating").click();
    await contains("[data-action-id='activeIconsNumber'] input").edit("5");
    expectIcons("active", 5, { icon: "star", filled: true });
    expectIcons("inactive", 0);

    // The inactive icons come back from an empty group.
    await contains("[data-action-id='activeIconsNumber'] input").edit("2");
    expectIcons("active", 2, { icon: "star", filled: true });
    expectIcons("inactive", 3, { icon: "star", filled: false });
});

test("custom icons are preserved after score change", async () => {
    await setupWebsiteBuilderWithSnippet("s_rating", { loadIframeBundles: true });
    await contains(":iframe .s_rating").click();

    await contains("[data-action-id='customIcon'][data-action-param='customActiveIcon']").click();
    await contains(".o_select_media_dialog .font-icons-icons span[data-icon='favorite']").click();
    expect(":iframe .s_rating_active_icons i").toHaveAttribute("data-icon", "favorite");
    expect(":iframe .s_rating_inactive_icons i").toHaveAttribute("data-icon", "star");

    await contains("[data-action-id='activeIconsNumber'] input").edit("4");
    expect(":iframe .s_rating_active_icons i").toHaveCount(4);
    expect(":iframe .s_rating_active_icons i").toHaveAttribute("data-icon", "favorite");
    expect(":iframe .s_rating_inactive_icons i").toHaveAttribute("data-icon", "star");
});

test("clicking on a rating icon updates the score and aria-label", async () => {
    const { getEditor } = await setupWebsiteBuilderWithSnippet("s_rating", {
        loadIframeBundles: true,
    });
    const editor = getEditor();

    await contains(":iframe .s_rating_inactive_icons i:nth-child(1)").click();
    expect(":iframe .s_rating_icons").toHaveAttribute("aria-label", "4 out of 5 stars");
    expect(":iframe .s_rating_icons i.oi-filled").toHaveCount(4);
    expect(":iframe .s_rating_icons i:not(.oi-filled)").toHaveCount(1);
    expect("[data-action-id='activeIconsNumber'] input").toHaveValue(4);

    await contains(":iframe .s_rating_active_icons i:nth-child(1)").click();
    expect(":iframe .s_rating_icons").toHaveAttribute("aria-label", "1 out of 5 stars");
    expect(":iframe .s_rating_icons i.oi-filled").toHaveCount(1);
    expect(":iframe .s_rating_icons i:not(.oi-filled)").toHaveCount(4);
    expect("[data-action-id='activeIconsNumber'] input").toHaveValue(1);

    undo(editor);
    await animationFrame();
    expect(":iframe .s_rating_icons").toHaveAttribute("aria-label", "4 out of 5 stars");
    expect(":iframe .s_rating_icons i.oi-filled").toHaveCount(4);
    expect("[data-action-id='activeIconsNumber'] input").toHaveValue(4);

    redo(editor);
    await animationFrame();
    expect(":iframe .s_rating_icons").toHaveAttribute("aria-label", "1 out of 5 stars");
    expect(":iframe .s_rating_icons i.oi-filled").toHaveCount(1);
    expect("[data-action-id='activeIconsNumber'] input").toHaveValue(1);
});

test("clicking the icon of the current score sets the score to 0", async () => {
    const { getEditor } = await setupWebsiteBuilderWithSnippet("s_rating", {
        loadIframeBundles: true,
    });
    const editor = getEditor();
    expect(":iframe .s_rating_icons").toHaveAttribute("aria-label", "3 out of 5 stars");

    await contains(":iframe .s_rating_active_icons i:nth-child(3)").click();
    expect(":iframe .s_rating_icons").toHaveAttribute("aria-label", "0 out of 5 stars");
    expect(":iframe .s_rating_icons i.oi-filled").toHaveCount(0);
    expect(":iframe .s_rating_icons i:not(.oi-filled)").toHaveCount(5);
    expect("[data-action-id='activeIconsNumber'] input").toHaveValue(0);

    undo(editor);
    await animationFrame();
    expect(":iframe .s_rating_icons").toHaveAttribute("aria-label", "3 out of 5 stars");
    expect(":iframe .s_rating_active_icons i").toHaveCount(3);
    expect("[data-action-id='activeIconsNumber'] input").toHaveValue(3);
});
