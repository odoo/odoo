import { expect, test } from "@odoo/hoot";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";
import { contains } from "@web/../tests/web_test_helpers";
import { animationFrame, setInputRange } from "@odoo/hoot-dom";

defineWebsiteModels();

test("Change avatars size", async () => {
    await setupWebsiteBuilderWithSnippet("s_avatars", { loadIframeBundles: true });
    await contains(":iframe .s_avatars").click();
    expect(".options-container[data-container-title='Avatars']").toHaveCount(1);
    expect("[data-label='Size'] input").toHaveValue(3);
    expect(":iframe .s_avatars").toHaveStyle("--avatars-size: 3rem");

    await setInputRange("[data-label='Size'] input", 2);
    await animationFrame();
    expect(":iframe .s_avatars").toHaveStyle("--avatars-size: 2rem");
});

test("Change avatars order", async () => {
    await setupWebsiteBuilderWithSnippet("s_avatars");
    await contains(":iframe .s_avatars").click();
    expect("[data-action-id='avatarsChangeOrder'].active").toHaveText("Last on top");
    expect(":iframe .s_avatars .s_avatars_avatar").toHaveStyle("z-index: auto");
    // Set the first avatar on top.
    await contains("[data-label='Order'] .dropdown").click();
    await contains(
        "[data-action-id='avatarsChangeOrder'][data-action-param='o_first_on_top']"
    ).click();
    expect(":iframe .s_avatars").toHaveClass("o_first_on_top");
    expect(":iframe .s_avatars .s_avatars_avatar:first").toHaveStyle("z-index: 4");
    expect(":iframe .s_avatars .s_avatars_avatar:last").toHaveStyle("z-index: 1");
    // Set back the last avatar on top.
    await contains("[data-label='Order'] .dropdown").click();
    await contains("[data-action-id='avatarsChangeOrder'][data-action-param='']").click();
    expect(":iframe .s_avatars").not.toHaveClass("o_first_on_top");
    expect(":iframe .s_avatars .s_avatars_avatar").toHaveStyle("z-index: auto");
});

test("Add/remove avatars", async () => {
    await setupWebsiteBuilderWithSnippet("s_avatars");
    await contains(":iframe .s_avatars").click();
    expect(":iframe .s_avatars .s_avatars_avatar.o_avatar").toHaveCount(3);

    // First put the first avatar on top (to test the z-index updates too).
    await contains("[data-label='Order'] .dropdown").click();
    await contains(
        "[data-action-id='avatarsChangeOrder'][data-action-param='o_first_on_top']"
    ).click();
    expect(":iframe .s_avatars").toHaveClass("o_first_on_top");

    // Remove an avatar.
    const removeButtonSelector =
        "[data-container-title='Avatars'] button[aria-label='Remove Avatar']";
    await contains(removeButtonSelector).click();
    expect(":iframe .s_avatars .s_avatars_avatar.o_avatar").toHaveCount(2);
    expect(":iframe .s_avatars .s_avatars_avatar.o_avatar:first").toHaveStyle("z-index: 3");
    expect(":iframe .s_avatars .s_avatars_avatar.o_avatar:last").toHaveStyle("z-index: 2");
    // Check that we cannot remove anymore with only one avatar remaining.
    await contains(removeButtonSelector).click();
    expect(":iframe .s_avatars .s_avatars_avatar.o_avatar").toHaveCount(1);
    expect(removeButtonSelector).toHaveAttribute("disabled");
    // Add an avatar.
    await contains("[data-container-title='Avatars'] button[aria-label='Add Avatar']").click();
    expect(":iframe .s_avatars .s_avatars_avatar.o_avatar").toHaveCount(2);
    expect(":iframe .s_avatars .s_avatars_avatar.o_avatar:first").toHaveStyle("z-index: 3");
    expect(":iframe .s_avatars .s_avatars_avatar.o_avatar:last").toHaveStyle("z-index: 2");
    expect(removeButtonSelector).not.toHaveAttribute("disabled");
});
