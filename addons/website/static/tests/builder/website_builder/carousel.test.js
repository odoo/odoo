import { expect, test } from "@odoo/hoot";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";
import { contains } from "@web/../tests/web_test_helpers";
import { queryFirst } from "@odoo/hoot-dom";

defineWebsiteModels();

const carouselStyle = `
    .slide:not(.carousel-instant) {
        --transition-duration: 600ms;
        .carousel-item {
            transition-duration: var(--transition-duration) !important;
        }
    }

    .carousel-instant {
        .carousel-item {
            transition: none;
        }
    }
`;

test("Test Carousel Option (s_carousel)", async () => {
    const { getEditableContent } = await setupWebsiteBuilderWithSnippet("s_carousel", {
        styleContent: carouselStyle,
    });
    const carouselEl = getEditableContent().querySelector(".carousel");
    await contains(":iframe .carousel").click();

    // Editing the Transition

    await contains(".o_hb_row[data-label='Transition'] button").click();
    await contains(".o_hb_select_dropdown_item:contains('None')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "10000");

    await contains(".o_hb_row[data-label='Transition'] button").click();
    await contains(".o_hb_select_dropdown_item:contains('Slide')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "10600");

    await contains(".o_hb_row[data-label='Transition'] button").click();
    await contains(".o_hb_select_dropdown_item:contains('Fade')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "10600");

    // Editing the Autoplay

    await contains(".o_hb_row[data-label='Autoplay'] button").click();
    await contains(".o_hb_select_dropdown_item:contains('Always')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "carousel");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "10600");

    await contains(".o_hb_row[data-label='Autoplay'] button").click();
    await contains(".o_hb_select_dropdown_item:contains('Never')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "false");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "10600");

    await contains(".o_hb_row[data-label='Autoplay'] button").click();
    await contains(".o_hb_select_dropdown_item:contains('After First Hover')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "10600");

    // Editing the Timespan

    await contains(".o_hb_row[data-label='Timespan'] input").edit("3");
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "3600");

    await contains(".o_hb_row[data-label='Timespan'] input").edit("0");
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "1600");

    // Editing the Speed

    expect(carouselEl).not.toHaveStyle("--transition-duration", { inline: true });
    expect(carouselEl).toHaveStyle({ "--transition-duration": "600ms" });

    await contains(".o_hb_row[data-label='Duration'] input[type='number']").edit("2");
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "3000");
    expect(carouselEl).toHaveStyle({ "--transition-duration": "2000ms" });

    await contains(".o_hb_row[data-label='Timespan'] input").edit("3");
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "5000");
    expect(carouselEl).toHaveStyle({ "--transition-duration": "2000ms" });

    // Autoplay: Never doesn't remove bs-interval

    await contains(".o_hb_row[data-label='Autoplay'] button").click();
    await contains(".o_hb_select_dropdown_item:contains('Never')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "false");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "5000");
    expect(carouselEl).toHaveStyle({ "--transition-duration": "2000ms" });
});

test("Test Carousel Option (s_image_gallery)", async () => {
    const { getEditableContent } = await setupWebsiteBuilderWithSnippet("s_image_gallery", {
        styleContent: carouselStyle,
    });
    const carouselEl = getEditableContent().querySelector(".carousel");
    await contains(":iframe .carousel").click();

    // Editing the Transition

    await contains(".o_hb_row[data-label='Transition'] button").click();
    await contains(".o_hb_select_dropdown_item:contains('None')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "carousel");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "1000");

    await contains(".o_hb_row[data-label='Transition'] button").click();
    await contains(".o_hb_select_dropdown_item:contains('Slide')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "carousel");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "1600");

    await contains(".o_hb_row[data-label='Transition'] button").click();
    await contains(".o_hb_select_dropdown_item:contains('Fade')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "carousel");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "1600");

    // Editing the Autoplay

    await contains(".o_hb_row[data-label='Autoplay'] button").click();
    await contains(".o_hb_select_dropdown_item:contains('Always')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "carousel");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "1600");

    await contains(".o_hb_row[data-label='Autoplay'] button").click();
    await contains(".o_hb_select_dropdown_item:contains('Never')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "false");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "1600");

    await contains(".o_hb_row[data-label='Autoplay'] button").click();
    await contains(".o_hb_select_dropdown_item:contains('After First Hover')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "1600");

    // Editing the Timespan

    await contains(".o_hb_row[data-label='Timespan'] input").edit("3");
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "3600");

    await contains(".o_hb_row[data-label='Timespan'] input").edit("0");
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "1600");

    // Editing the Speed

    expect(carouselEl).not.toHaveStyle("--transition-duration", { inline: true });
    expect(carouselEl).toHaveStyle({ "--transition-duration": "600ms" });

    await contains(".o_hb_row[data-label='Duration'] input[type='number']").edit("2");
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "3000");
    expect(carouselEl).toHaveStyle({ "--transition-duration": "2000ms" });

    await contains(".o_hb_row[data-label='Timespan'] input").edit("3");
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "5000");
    expect(carouselEl).toHaveStyle({ "--transition-duration": "2000ms" });

    // Autoplay: Never doesn't remove bs-interval

    await contains(".o_hb_row[data-label='Autoplay'] button").click();
    await contains(".o_hb_select_dropdown_item:contains('Never')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "false");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "5000");
    expect(carouselEl).toHaveStyle({ "--transition-duration": "2000ms" });
});

test("Test carousel item height matches configured section height", async () => {
    await setupWebsiteBuilderWithSnippet("s_carousel", { loadIframeBundles: true });
    await contains(":iframe .s_carousel").click();

    const carouselItemEl = queryFirst(":iframe .carousel-item");
    const iframeHeight = carouselItemEl.ownerDocument.defaultView.innerHeight;

    await contains("button[data-action-param='o_full_screen_height']").click();
    expect(carouselItemEl.getBoundingClientRect().height).toBeCloseTo(iframeHeight, {
        margin: 1,
    });

    await contains("button[data-action-param='o_three_quarter_height']").click();
    expect(carouselItemEl.getBoundingClientRect().height).toBeCloseTo(iframeHeight * 0.75, {
        margin: 1,
    });
});
