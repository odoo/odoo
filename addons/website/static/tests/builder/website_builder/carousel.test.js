import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { CarouselOptionPlugin } from "@website/builder/plugins/carousel_option_plugin";

defineWebsiteModels();

test("Test Carousel Option (s_carousel)", async () => {
    const { getEditableContent } = await setupWebsiteBuilderWithSnippet("s_carousel", {
        loadIframeBundles: true,
    });
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

test("Test Carousel Option buttons get disabled until action finished", async () => {
    patchWithCleanup(CarouselOptionPlugin.prototype, {
        async addSlide(carouselEl) {
            await animationFrame();
            const backwardButton = document.querySelector("button.o_slide_move_backward");
            expect(backwardButton).toHaveClass("disabled", {
                message: "Add Slide button should be disabled during transition",
            });
        },
    });
    const { getEditableContent } = await setupWebsiteBuilderWithSnippet("s_carousel", {
        loadIframeBundles: true,
    });
    getEditableContent().querySelector(".carousel");
    await contains(":iframe .carousel .carousel-item").click();
    await contains(".options-container button.o_slide_add").click();
});

test("Test Carousel Option (s_image_gallery)", async () => {
    const { getEditableContent } = await setupWebsiteBuilderWithSnippet("s_image_gallery", {
        loadIframeBundles: true,
    });
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
