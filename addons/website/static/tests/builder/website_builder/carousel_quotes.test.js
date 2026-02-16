import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";
import { getDragMoveHelper } from "@html_builder/../tests/helpers";

defineWebsiteModels();

function checkDatasetIndex(carouselSlideEls) {
    carouselSlideEls.forEach((carouselSlideEl, index) => {
        expect(carouselSlideEl.dataset.index).toBe(index.toString());
    });
}

function isSingleMode(carouselEl, count) {
    const expectedStyle = `${100 / count}%`;
    return (
        carouselEl.classList.contains("o_carousel_multi_items") &&
        carouselEl.style.getPropertyValue("--o-carousel-item-width-percentage") === expectedStyle
    );
}

async function testQuoteCarousel(snippetName, getEditableContent) {
    const editableEl = getEditableContent();
    await contains(`:iframe section[data-snippet="${snippetName}"]`).click();
    await contains("[data-label='Layout'] .dropdown-toggle").click();
    await contains(
        ".o-overlay-item [data-action-id='updateQuotesCarouselLayout']:nth-child(4)"
    ).click();

    // Assert "all" mode layout
    const carouselEl = editableEl.querySelector(".s_quotes_carousel");
    expect(isSingleMode(carouselEl, 4)).toBe(false);
    const rowEls = editableEl.querySelectorAll(".carousel-item .row");
    expect(rowEls[0].querySelectorAll(".carousel-slide").length).toBe(4);
    const carouselSlideEls = carouselEl.querySelectorAll(".carousel-item .carousel-slide");
    checkDatasetIndex(carouselSlideEls);

    // Test slide reorder in "all" mode
    await contains(":iframe .carousel-item blockquote").click();
    const { moveTo, drop } = await contains(".o_overlay_options .o_move_handle").drag();
    await moveTo(":iframe .s_quotes_carousel .carousel-item .row:last-child");
    await drop(getDragMoveHelper());
    checkDatasetIndex(editableEl.querySelectorAll(".carousel-item .carousel-slide"));
    await contains(".overlay .o-we-toolbar button[title='Move up']").click();
    checkDatasetIndex(editableEl.querySelectorAll(".carousel-item .carousel-slide"));

    await contains(
        "[data-label='Scrolling Mode'] [data-action-id='updateQuotesCarouselLayout']:nth-child(2)"
    ).click();

    // Assert "single" mode layout
    expect(isSingleMode(carouselEl, 4)).toBe(true);
    const carouselItemEls = carouselEl.querySelectorAll(".carousel-item.carousel-slide");
    const indicatorContainerEl = editableEl.querySelector(".indicators-container");
    expect(indicatorContainerEl).toHaveClass("d-none");
    checkDatasetIndex(carouselItemEls);

    // Removed the elements on which testing is done to avoid interference with
    // other tests
    await contains(".oe_snippet_remove").click();
}

test("Quote carousel layout and it's related options test", async () => {
    const carousels = ["s_quotes_carousel", "s_quotes_carousel_minimal"];
    const { getEditableContent } = await setupWebsiteBuilderWithSnippet(carousels);
    for (const carousel of carousels) {
        await testQuoteCarousel(carousel, getEditableContent);
    }
});

// TODO: Add the following test cases after task-5269350 by SHSA is merged.
// 1. Load the "website.carousel_slider" interaction.
// 2. Click on a slide and expect ".carousel-slide.o-focused-slide".
// 3. Click the next arrow and expect ".carousel-slide.o-focused-slide.active".
