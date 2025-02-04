import { describe, expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "../helpers";

defineWebsiteModels();

const base64Img =
    "data:image/png;base64, iVBORw0KGgoAAAANSUhEUgAAAAUA\n        AAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO\n            9TXL0Y4OHwAAAABJRU5ErkJggg==";

const styleContent = `
.o_animate {
    animation-duration: 1s;
    --wanim-intensity: 50;
}
`;

test("visibility of animation animation=none", async () => {
    await setupWebsiteBuilder(`
        <div class="test-options-target">
            <img src='${base64Img}'>
        </div>
    `);
    await contains(":iframe .test-options-target img").click();

    expect(".options-container [data-label='Effect']").not.toBeVisible();
    expect(".options-container [data-label='Direction']").not.toBeVisible();
    expect(".options-container [data-label='Trigger']").not.toBeVisible();
    expect(".options-container [data-label='Intensity']").not.toBeVisible();
    expect(".options-container [data-label='Start After']").not.toBeVisible();
    expect(".options-container [data-label='Duration']").not.toBeVisible();
});
describe("onAppearance", () => {
    test("visibility of animation animation=onAppearance", async () => {
        await setupWebsiteBuilder(
            `
                <div class="test-options-target">
                    <img src='${base64Img}'>
                </div>
            `,
            { styleContent }
        );
        await contains(":iframe .test-options-target img").click();

        await contains(".options-container [data-label='Animation'] .dropdown-toggle").click();
        await contains(".o-dropdown--menu [data-action-value='onAppearance']").click();
        expect(".options-container [data-label='Animation'] .o-dropdown").toHaveText(
            "On Appearance"
        );

        expect(".options-container [data-label='Effect'] .o-dropdown").toHaveText("Fade");
        expect(".options-container [data-label='Direction'] .o-dropdown").toHaveText("In place");
        expect(".options-container [data-label='Trigger'] .o-dropdown").toHaveText(
            "First Time Only"
        );
        expect(".options-container [data-label='Intensity']").not.toBeVisible();
        expect(".options-container [data-label='Scroll Zone']").not.toBeVisible();
        expect(".options-container [data-label='Start After'] input").toHaveValue("0");
        expect(".options-container [data-label='Duration'] input").toHaveValue("1");
    });
    test("visibility of animation animation=onAppearance effect=slide", async () => {
        await setupWebsiteBuilder(
            `
                <div class="test-options-target">
                    <img src='${base64Img}'>
                </div>
            `,
            { styleContent }
        );
        await contains(":iframe .test-options-target img").click();

        await contains(".options-container [data-label='Animation'] .dropdown-toggle").click();
        await contains(".o-dropdown--menu [data-action-value='onAppearance']").click();

        await contains(".options-container [data-label='Effect'] .dropdown-toggle").click();
        await contains(".o-dropdown--menu [data-action-value='o_anim_slide_in']").click();
        expect(".options-container [data-label='Effect'] .o-dropdown").toHaveText("Slide");

        expect(".options-container [data-label='Direction'] .o-dropdown").toHaveText("From right");
        expect(".options-container [data-label='Trigger'] .o-dropdown").toHaveText(
            "First Time Only"
        );
        expect(".options-container [data-label='Intensity'] input").toHaveValue(50);
        expect(".options-container [data-label='Scroll Zone']").not.toBeVisible();
        expect(".options-container [data-label='Start After'] input").toHaveValue("0");
        expect(".options-container [data-label='Duration'] input").toHaveValue("1");
    });
    test("visibility of animation animation=onAppearance effect=bounce", async () => {
        await setupWebsiteBuilder(
            `
                <div class="test-options-target">
                    <img src='${base64Img}'>
                </div>
            `,
            { styleContent }
        );
        await contains(":iframe .test-options-target img").click();

        await contains(".options-container [data-label='Animation'] .dropdown-toggle").click();
        await contains(".o-dropdown--menu [data-action-value='onAppearance']").click();

        await contains(".options-container [data-label='Effect'] .dropdown-toggle").click();
        await contains(".o-dropdown--menu [data-action-value='o_anim_bounce_in']").click();
        expect(".options-container [data-label='Effect'] .o-dropdown").toHaveText("Bounce");

        expect(".options-container [data-label='Direction'] .o-dropdown").toHaveText("In place");
        expect(".options-container [data-label='Trigger'] .o-dropdown").toHaveText(
            "First Time Only"
        );
        expect(".options-container [data-label='Intensity'] input").toHaveValue(50);
        expect(".options-container [data-label='Scroll Zone']").not.toBeVisible();
        expect(".options-container [data-label='Start After'] input").toHaveValue("0");
        expect(".options-container [data-label='Duration'] input").toHaveValue("1");
    });
    test("visibility of animation animation=onAppearance effect=flash", async () => {
        await setupWebsiteBuilder(
            `
                <div class="test-options-target">
                    <img src='${base64Img}'>
                </div>
            `,
            { styleContent }
        );
        await contains(":iframe .test-options-target img").click();

        await contains(".options-container [data-label='Animation'] .dropdown-toggle").click();
        await contains(".o-dropdown--menu [data-action-value='onAppearance']").click();

        await contains(".options-container [data-label='Effect'] .dropdown-toggle").click();
        await contains(".o-dropdown--menu [data-action-value='o_anim_flash']").click();
        expect(".options-container [data-label='Effect'] .o-dropdown").toHaveText("Flash");

        expect(".options-container [data-label='Direction']").not.toBeVisible();
        expect(".options-container [data-label='Trigger'] .o-dropdown").toHaveText(
            "First Time Only"
        );
        expect(".options-container [data-label='Intensity'] input").toHaveValue(50);
        expect(".options-container [data-label='Scroll Zone']").not.toBeVisible();
        expect(".options-container [data-label='Start After'] input").toHaveValue("0");
        expect(".options-container [data-label='Duration'] input").toHaveValue("1");
    });
});
test("visibility of animation animation=onScroll", async () => {
    await setupWebsiteBuilder(`
        <div class="test-options-target">
            <img src='${base64Img}'>
        </div>
    `);
    await contains(":iframe .test-options-target img").click();

    await contains(".options-container [data-label='Animation'] .dropdown-toggle").click();
    await contains(".o-dropdown--menu [data-action-value='onScroll']").click();
    expect(".options-container [data-label='Animation'] .o-dropdown").toHaveText("On Scroll");

    expect(".options-container [data-label='Effect'] .o-dropdown").toHaveText("Fade");
    expect(".options-container [data-label='Direction'] .o-dropdown").toHaveText("In place");

    expect(".options-container [data-label='Trigger']").not.toBeVisible();
    expect(".options-container [data-label='Intensity']").not.toBeVisible();
    expect(".options-container [data-label='Start After']").not.toBeVisible();
    expect(".options-container [data-label='Duration']").not.toBeVisible();

    expect(".options-container [data-label='Scroll Zone']").toBeVisible();
});
test("visibility of animation animation=onHover", async () => {
    await setupWebsiteBuilder(`
        <div class="test-options-target">
            <img src='${base64Img}'>
        </div>
    `);
    await contains(":iframe .test-options-target img").click();

    await contains(".options-container [data-label='Animation'] .dropdown-toggle").click();
    await contains(".o-dropdown--menu [data-action-value='onHover']").click();
    expect(".options-container [data-label='Animation'] .o-dropdown").toHaveText("On Hover");

    expect(".options-container [data-label='Effect']").not.toBeVisible();
    expect(".options-container [data-label='Direction']").not.toBeVisible();
    expect(".options-container [data-label='Trigger']").not.toBeVisible();
    expect(".options-container [data-label='Intensity']").not.toBeVisible();
    expect(".options-container [data-label='Scroll Zone']").not.toBeVisible();
    expect(".options-container [data-label='Start After']").not.toBeVisible();
    expect(".options-container [data-label='Duration']").not.toBeVisible();

    // todo: check all the hover options
});

test("image should not be lazy onAppearance", async () => {
    await setupWebsiteBuilder(`
        <div class="test-options-target">
            <img src='${base64Img}'>
        </div>
    `);
    await contains(":iframe .test-options-target img").click();

    expect(":iframe .test-options-target img").toHaveProperty("loading", "auto");

    await contains(".options-container [data-label='Animation'] .dropdown-toggle").click();
    await contains(".o-dropdown--menu [data-action-value='onAppearance']").click();

    expect(":iframe .test-options-target img").toHaveProperty("loading", "eager");

    await contains(".options-container [data-label='Animation'] .dropdown-toggle").click();
    await contains(".o-dropdown--menu [data-action-value='']").click();

    expect(":iframe .test-options-target img").toHaveProperty("loading", "auto");
});

test("o_animate should be normalized with loading=eager", async () => {
    await setupWebsiteBuilder(`
        <div class="test-options-target">
            <img class="o_animate" src='${base64Img}'>
        </div>
    `);
    // Should be normalized
    expect(":iframe .test-options-target img").toHaveProperty("loading", "eager");
});
