import { describe, expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "../website_helpers";
import { animationFrame, queryFirst } from "@odoo/hoot-dom";
import { mockFetch } from "@odoo/hoot-mock";

defineWebsiteModels();

const base64Img =
    "data:image/png;base64, iVBORw0KGgoAAAANSUhEUgAAAAUA\n        AAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO\n            9TXL0Y4OHwAAAABJRU5ErkJggg==";

const testImg = `<img data-original-id="1" data-mimetype="image/png" src='/base/static/img/logo_white.png'>`;

const styleContent = `
.o_animate {
    animation-duration: 1s;
    --wanim-intensity: 50;
}
`;

test("visibility of animation animation=none", async () => {
    await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
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
                    ${testImg}
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
                    ${testImg}
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
                    ${testImg}
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
                    ${testImg}
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
            ${testImg}
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
test("animation=onScroll should not be visible when the animation is limited", async () => {
    await setupWebsiteBuilder(
        `
                <div class="test-options-target">
                    ${testImg}
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

    await contains(".options-container [data-label='Animation'] .dropdown-toggle").click();
    expect(".o-dropdown--menu [data-action-value='onScroll']").not.toBeVisible();
});
test("visibility of animation animation=onHover", async () => {
    await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
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
test("animation=onHover should not be visible when the image is a device shape", async () => {
    await setupWebsiteBuilder(`
        <div class="test-options-target">
            <img data-shape="html_builder/devices/iphone_front_portrait" src='${base64Img}'>
        </div>
    `);
    await contains(":iframe .test-options-target img").click();

    await contains(".options-container [data-label='Animation'] .dropdown-toggle").click();
    expect(".o-dropdown--menu [data-action-value='onHover']").not.toBeVisible();
});
test("animation=onHover should not be visible when the image has a wrong mimetype", async () => {
    await setupWebsiteBuilder(`
        <div class="test-options-target">
            <img data-original-id="1" data-mimetype="foo/bar" src='${base64Img}'>
        </div>
    `);
    await contains(":iframe .test-options-target img").click();

    await contains(".options-container [data-label='Animation'] .dropdown-toggle").click();
    expect(".o-dropdown--menu [data-action-value='onHover']").not.toBeVisible();
});
test("animation=onHover should not be visible when the image has a cors protected image", async () => {
    await setupWebsiteBuilder(`
        <div class="test-options-target">
            <img data-original-id="1" src='/web/image/0-redirect/foo.jpg'>
        </div>
    `);
    mockFetch((route) => {
        expect.step(route);
        throw new Error("simulated cors error");
    });
    await contains(":iframe .test-options-target img").click();

    await contains(".options-container [data-label='Animation'] .dropdown-toggle").click();
    expect.verifySteps(["/web/image/0-redirect/foo.jpg"]);
    expect(".o-dropdown--menu [data-action-value='onHover']").not.toBeVisible();
});

test("image should not be lazy onAppearance", async () => {
    await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
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

test("should not show the animation options if the image has a parent [data-oe-type='image']", async () => {
    const { getEditor } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
    const editor = getEditor();
    await contains(":iframe .test-options-target img").click();

    await animationFrame();
    expect(".options-container [data-label='Animation'] .dropdown-toggle").toBeVisible();
    const optionTarget = queryFirst(":iframe .test-options-target");
    optionTarget.setAttribute("data-oe-type", "image");
    editor.shared.history.addStep();
    await animationFrame();
    expect(".options-container [data-label='Animation'] .dropdown-toggle").not.toBeVisible();
});

test("should not show the animation options if the image has is [data-oe-xpath]", async () => {
    const { getEditor } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
    const editor = getEditor();
    await contains(":iframe .test-options-target img").click();

    await animationFrame();
    expect(".options-container [data-label='Animation'] .dropdown-toggle").toBeVisible();
    const optionTarget = queryFirst(":iframe .test-options-target img");
    optionTarget.setAttribute("data-oe-xpath", "/foo/bar");
    editor.shared.history.addStep();
    await animationFrame();
    expect(".options-container [data-label='Animation'] .dropdown-toggle").not.toBeVisible();
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
