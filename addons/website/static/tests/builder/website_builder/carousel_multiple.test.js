import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, setInputRange } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";
import { getCarouselCenteringIndex } from "@website/utils/misc";

defineWebsiteModels();

describe("Carousel Multiple snippet options", () => {
    test("Change slides to display", async () => {
        await setupWebsiteBuilderWithSnippet("s_carousel_multiple", { loadIframeBundles: true });
        expect(":iframe .s_carousel_multiple").toHaveClass("o_displayed_items_4");
        await contains(":iframe .s_carousel_multiple").click();
        await contains(".hb-row[data-label='Displayed slides'] button").click();
        await contains(".o-hb-select-dropdown-item:contains('2')").click();
        expect(":iframe .s_carousel_multiple").toHaveClass("o_displayed_items_2");
        expect(":iframe .s_carousel_multiple").not.toHaveClass("o_displayed_items_4");
    });

    test("Spacing Option", async () => {
        await setupWebsiteBuilderWithSnippet("s_carousel_multiple", { loadIframeBundles: true });
        expect(":iframe .s_carousel_multiple").toHaveStyle({
            "--carousel-multiple-items-gap": "16px",
        });

        await contains(":iframe .s_carousel_multiple").click();
        await setInputRange(".hb-row[data-label='Spacing'] input", "24");
        await animationFrame();
        expect(":iframe .s_carousel_multiple").toHaveStyle({
            "--carousel-multiple-items-gap": "24px",
        });
    });

    test("Controllers visibility", async () => {
        await setupWebsiteBuilderWithSnippet("s_carousel_multiple", { loadIframeBundles: true });

        await contains(":iframe .s_carousel_multiple").click();
        expect(":iframe .carousel-control-prev").toBeVisible();
        expect(":iframe .carousel-control-next").toBeVisible();
        expect(":iframe .carousel-indicators").toBeVisible();

        await contains(".hb-row[data-label='Arrows'] button").click();
        await contains(".o-hb-select-dropdown-item:contains('Hidden')").click();
        expect(":iframe .carousel-control-prev").not.toBeVisible();
        expect(":iframe .carousel-control-next").not.toBeVisible();

        await contains(".hb-row[data-label='Indicators'] button").click();
        await contains(".o-hb-select-dropdown-item:contains('Hidden')").click();
        expect(":iframe .carousel-indicators").not.toBeVisible();
    });
});

function createCarousel(nbItemsPerSlide, nbItems) {
    const carouselEl = document.createElement("div");
    carouselEl.className = "carousel";
    carouselEl.style.setProperty("--carousel-multiple-items-per-slide", nbItemsPerSlide);

    for (let i = 0; i < nbItems; i++) {
        const itemEl = document.createElement("div");
        itemEl.className = "carousel-item";
        carouselEl.appendChild(itemEl);
    }

    document.body.appendChild(carouselEl);
    return carouselEl;
}

describe("tests for the getCarouselCenteringIndex util function", () => {
    test("returns null when all slides visible", () => {
        const carouselEl = createCarousel(5, 5);
        expect(getCarouselCenteringIndex(carouselEl.children[2])).toBe(null);
    });

    test("centers target with odd visibleSlides", () => {
        const carouselEl = createCarousel(3, 10);
        expect(getCarouselCenteringIndex(carouselEl.children[4])).toBe(3);
    });

    test("centers target with even visibleSlides", () => {
        const carouselEl = createCarousel(4, 10);
        expect(getCarouselCenteringIndex(carouselEl.children[5])).toBe(3);
    });

    test("clamps to 0 for early items and to the last slide for late items", () => {
        const carouselEl = createCarousel(3, 10);
        expect(getCarouselCenteringIndex(carouselEl.children[0])).toBe(0);
        expect(getCarouselCenteringIndex(carouselEl.children[1])).toBe(0);
        // since we have 3 visible carousel items on screen and we have 10
        // items in total, last 3 items should stay on the 7th 'slide'
        expect(getCarouselCenteringIndex(carouselEl.children[8])).toBe(7);
        expect(getCarouselCenteringIndex(carouselEl.children[9])).toBe(7);
    });

    test("handles single visible slide", () => {
        const carouselEl = createCarousel(1, 10);
        expect(getCarouselCenteringIndex(carouselEl.children[0])).toBe(0);
        expect(getCarouselCenteringIndex(carouselEl.children[2])).toBe(2);
        expect(getCarouselCenteringIndex(carouselEl.children[4])).toBe(4);
    });
});
