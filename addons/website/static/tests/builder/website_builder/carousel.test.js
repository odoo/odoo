import { expect, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-dom";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { CarouselOptionPlugin } from "@website/builder/plugins/carousel_option_plugin";

defineWebsiteModels();

test("Test Carousel Option (s_carousel)", async () => {
    const { getEditableContent } = await setupWebsiteBuilderWithSnippet("s_carousel");
    const carouselEl = getEditableContent().querySelector(".carousel");
    await contains(":iframe .carousel").click();

    // Editing the Transition

    await contains(".hb-row[data-label='Transition'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('None')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "10000");

    await contains(".hb-row[data-label='Transition'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('Slide')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "10000");

    await contains(".hb-row[data-label='Transition'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('Fade')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "10000");

    // Editing the Autoplay

    await contains(".hb-row[data-label='Autoplay'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('Always')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "carousel");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "10000");

    await contains(".hb-row[data-label='Autoplay'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('Never')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "false");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "10000");

    await contains(".hb-row[data-label='Autoplay'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('After First Hover')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "10000");

    // Editing the Speed

    await contains(".hb-row[data-label='Speed'] input").edit("3");
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "3000");

    await contains(".hb-row[data-label='Speed'] input").edit("0");
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "1000");

    // Autoplay: Never doesn't remove bs-interval

    await contains(".hb-row[data-label='Autoplay'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('Never')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "false");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "1000");
});

test("Carousel slide buttons are disabled while a slide transition is running", async () => {
    // Hold every slide transition until the test releases it.
    let slideDef;
    patchWithCleanup(CarouselOptionPlugin.prototype, {
        async slide() {
            expect.step("slide");
            await slideDef;
            await super.slide(...arguments);
            expect.step("slid");
        },
    });
    const { waitSidebarUpdated } = await setupWebsiteBuilderWithSnippet("s_carousel", {
        loadIframeBundles: true,
        loadAssetsFrontendJS: true,
    });
    await contains(":iframe .carousel-item").click();

    const buttonSelectors = [
        "button.o_slide_move_backward",
        "button.o_slide_move_forward",
        "button.o_slide_add",
        "button.o_slide_remove",
    ];
    for (const clickedSelector of [
        "button.o_slide_add",
        "button.o_slide_remove",
        "button.o_slide_move_backward",
        "button.o_slide_move_forward",
    ]) {
        slideDef = new Deferred();
        await contains(clickedSelector).click();
        await expect.waitForSteps(["slide"]);
        await animationFrame();
        for (const selector of buttonSelectors) {
            expect(selector).toHaveClass("disabled", {
                message: `${selector} should be disabled while ${clickedSelector} is running`,
            });
        }

        slideDef.resolve();
        await expect.waitForSteps(["slid"]);
        await waitSidebarUpdated();
        for (const selector of buttonSelectors) {
            expect(selector).not.toHaveClass("disabled", {
                message: `${selector} should be enabled again once ${clickedSelector} is done`,
            });
        }
    }
    expect(":iframe .carousel-item").toHaveCount(3);
});

test("Test Carousel Option (s_image_gallery)", async () => {
    const { getEditableContent } = await setupWebsiteBuilderWithSnippet("s_image_gallery");
    const carouselEl = getEditableContent().querySelector(".carousel");
    await contains(":iframe .carousel").click();

    // Editing the Transition

    await contains(".hb-row[data-label='Transition'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('None')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "carousel");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "0");

    await contains(".hb-row[data-label='Transition'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('Slide')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "carousel");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "0");

    await contains(".hb-row[data-label='Transition'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('Fade')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "carousel");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "0");

    // Editing the Autoplay

    await contains(".hb-row[data-label='Autoplay'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('Always')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "carousel");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "0");

    await contains(".hb-row[data-label='Autoplay'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('Never')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "false");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "0");

    await contains(".hb-row[data-label='Autoplay'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('After First Hover')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "0");

    // Editing the Speed

    await contains(".hb-row[data-label='Speed'] input").edit("3");
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "3000");

    await contains(".hb-row[data-label='Speed'] input").edit("0");
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "1000");

    // Autoplay: Never doesn't remove bs-interval

    await contains(".hb-row[data-label='Autoplay'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('Never')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "false");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "1000");
});
