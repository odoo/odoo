import { expect, test } from "@odoo/hoot";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";
import { contains } from "@web/../tests/web_test_helpers";

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

    await contains(".hb-row[data-label='Transition'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('None')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "10000");

    await contains(".hb-row[data-label='Transition'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('Slide')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "10600");

    await contains(".hb-row[data-label='Transition'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('Fade')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "10600");

    // Editing the Autoplay

    await contains(".hb-row[data-label='Autoplay'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('Always')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "carousel");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "10600");

    await contains(".hb-row[data-label='Autoplay'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('Never')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "false");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "10600");

    await contains(".hb-row[data-label='Autoplay'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('After First Hover')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "10600");

    // Editing the Timespan

    await contains(".hb-row[data-label='Timespan'] input").edit("3");
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "3600");

    await contains(".hb-row[data-label='Timespan'] input").edit("0");
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "1600");

    // Editing the Speed

    expect(carouselEl).not.toHaveStyle("--transition-duration", { inline: true });
    expect(carouselEl).toHaveStyle({ "--transition-duration": "600ms" });

    await contains(".hb-row[data-label='Duration'] input[type='number']").edit("2");
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "3000");
    expect(carouselEl).toHaveStyle({ "--transition-duration": "2000ms" });

    await contains(".hb-row[data-label='Timespan'] input").edit("3");
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "5000");
    expect(carouselEl).toHaveStyle({ "--transition-duration": "2000ms" });

    // Autoplay: Never doesn't remove bs-interval

    await contains(".hb-row[data-label='Autoplay'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('Never')").click();
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

    await contains(".hb-row[data-label='Transition'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('None')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "carousel");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "1000");

    await contains(".hb-row[data-label='Transition'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('Slide')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "carousel");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "1600");

    await contains(".hb-row[data-label='Transition'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('Fade')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "carousel");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "1600");

    // Editing the Autoplay

    await contains(".hb-row[data-label='Autoplay'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('Always')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "carousel");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "1600");

    await contains(".hb-row[data-label='Autoplay'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('Never')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "false");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "1600");

    await contains(".hb-row[data-label='Autoplay'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('After First Hover')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "1600");

    // Editing the Timespan

    await contains(".hb-row[data-label='Timespan'] input").edit("3");
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "3600");

    await contains(".hb-row[data-label='Timespan'] input").edit("0");
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "1600");

    // Editing the Speed

    expect(carouselEl).not.toHaveStyle("--transition-duration", { inline: true });
    expect(carouselEl).toHaveStyle({ "--transition-duration": "600ms" });

    await contains(".hb-row[data-label='Duration'] input[type='number']").edit("2");
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "3000");
    expect(carouselEl).toHaveStyle({ "--transition-duration": "2000ms" });

    await contains(".hb-row[data-label='Timespan'] input").edit("3");
    expect(carouselEl).toHaveAttribute("data-bs-ride", "true");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "5000");
    expect(carouselEl).toHaveStyle({ "--transition-duration": "2000ms" });

    // Autoplay: Never doesn't remove bs-interval

    await contains(".hb-row[data-label='Autoplay'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('Never')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "false");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "5000");
    expect(carouselEl).toHaveStyle({ "--transition-duration": "2000ms" });
});
