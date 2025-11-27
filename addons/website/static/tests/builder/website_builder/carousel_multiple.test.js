import { expect, test } from "@odoo/hoot";
import { animationFrame, queryOne, setInputRange } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

const defaultCarouselMultipleSnippet = `
    <section class="s_carousel_multiple_wrapper pt48 pb48 overflow-hidden" style="--o-carousel-multiple-items-gap: 16px;">
        <div id="myCarousel123" class="s_carousel_multiple s_carousel_default carousel carousel-dark slide container o_displayed_items_4" data-bs-ride="false" data-bs-interval="0" style="--o-carousel-multiple-items: 1;">
            <div class="carousel-inner d-flex h-auto">
                <div class="s_carousel_multiple_item carousel-item active d-block flex-shrink-0 h-auto m-0 p-0 float-none" data-name="Slide">
                    <div class="s_card card">
                        <div class="card-body">
                            <h2 class="card-title">#1</h2>
                            <p class="card-text">Card content 1</p>
                        </div>
                    </div>
                </div>
                <div class="s_carousel_multiple_item carousel-item d-block flex-shrink-0 h-auto m-0 p-0 float-none" data-name="Slide">
                    <div class="s_card card">
                        <div class="card-body">
                            <h2 class="card-title">#2</h2>
                            <p class="card-text">Card content 2</p>
                        </div>
                    </div>
                </div>
                <div class="s_carousel_multiple_item carousel-item d-block flex-shrink-0 h-auto m-0 p-0 float-none" data-name="Slide">
                    <div class="s_card card">
                        <div class="card-body">
                            <h2 class="card-title">#3</h2>
                            <p class="card-text">Card content 3</p>
                        </div>
                    </div>
                </div>
                <div class="s_carousel_multiple_item carousel-item d-block flex-shrink-0 h-auto m-0 p-0 float-none" data-name="Slide">
                    <div class="s_card card">
                        <div class="card-body">
                            <h2 class="card-title">#4</h2>
                            <p class="card-text">Card content 4</p>
                        </div>
                    </div>
                </div>
                <div class="s_carousel_multiple_item carousel-item d-block flex-shrink-0 h-auto m-0 p-0 float-none" data-name="Slide">
                    <div class="s_card card">
                        <div class="card-body">
                            <h2 class="card-title">#5</h2>
                            <p class="card-text">Card content 5</p>
                        </div>
                    </div>
                </div>
            </div>
            <div class="o_horizontal_controllers container w-100 mt-3">
                <div class="o_horizontal_controllers_row row gap-3 gap-lg-5 justify-content-between flex-nowrap flex-row-reverse mx-0">
                    <div class="o_arrows_wrapper d-contents d-md-flex gap-2 w-auto p-0">
                        <button class="carousel-control-prev" data-bs-target="#myCarousel123" data-bs-slide="prev" aria-label="Previous">
                            <span class="carousel-control-prev-icon" aria-hidden="true"/>
                        </button>
                        <button class="carousel-control-next" data-bs-target="#myCarousel123" data-bs-slide="next" aria-label="Next">
                            <span class="carousel-control-next-icon" aria-hidden="true"/>
                        </button>
                    </div>
                    <div class="carousel-indicators position-relative align-items-center flex-shrink-1 w-100 w-md-auto">
                        <button type="button" data-bs-target="#myCarousel123" data-bs-slide-to="0" class="active" aria-label="Carousel indicator"/>
                        <button type="button" data-bs-target="#myCarousel123" data-bs-slide-to="1" aria-label="Carousel indicator"/>
                        <button type="button" data-bs-target="#myCarousel123" data-bs-slide-to="2" aria-label="Carousel indicator"/>
                        <button type="button" data-bs-target="#myCarousel123" data-bs-slide-to="3" aria-label="Carousel indicator"/>
                        <button type="button" data-bs-target="#myCarousel123" data-bs-slide-to="4" aria-label="Carousel indicator"/>
                    </div>
                </div>
            </div>
        </div>
    </section>`;

test("Change slides to display", async () => {
    await setupWebsiteBuilder(defaultCarouselMultipleSnippet);
    expect(":iframe .s_carousel_multiple").toHaveClass("o_displayed_items_4");

    await contains(":iframe .s_carousel_multiple").click();

    await contains(".hb-row[data-label='Displayed slides'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('2')").click();
    expect(":iframe .s_carousel_multiple").toHaveClass("o_displayed_items_2");
    expect(":iframe .s_carousel_multiple").not.toHaveClass("o_displayed_items_4");

    await contains(".hb-row[data-label='Displayed slides'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('3')").click();
    expect(":iframe .s_carousel_multiple").toHaveClass("o_displayed_items_3");
    expect(":iframe .s_carousel_multiple").not.toHaveClass("o_displayed_items_2");
});

test("Spacing Option", async () => {
    await setupWebsiteBuilder(defaultCarouselMultipleSnippet);
    const carouselEl = ":iframe .s_carousel_multiple";
    expect(carouselEl).toHaveStyle({ "--o-carousel-multiple-items-gap": "16px" });
    await contains(carouselEl).click();

    const inputRange = queryOne(".hb-row[data-label='Spacing'] input[type='range']");
    await setInputRange(inputRange, "24");
    await animationFrame();

    expect(carouselEl).toHaveStyle({ "--o-carousel-multiple-items-gap": "24px" });
});

test("Add slide", async () => {
    await setupWebsiteBuilder(defaultCarouselMultipleSnippet);
    await contains(":iframe .s_carousel_multiple_item.active").click();
    expect(":iframe .s_carousel_multiple_item").toHaveCount(5);

    await contains(".hb-row .o-hb-btn[title='Add Slide']").click();
    expect(":iframe .s_carousel_multiple_item").toHaveCount(6);
    expect(":iframe .carousel-indicators button").toHaveCount(6);
});

test("Remove slide", async () => {
    await setupWebsiteBuilder(defaultCarouselMultipleSnippet);
    expect(":iframe .s_carousel_multiple_item").toHaveCount(5);
    await contains(":iframe .s_carousel_multiple_item.active").click();

    await contains(".options-container .btn[title='Remove Slide']").click();

    expect(":iframe .s_carousel_multiple_item").toHaveCount(4);

    expect(":iframe .carousel-indicators button").toHaveCount(4);
});

test("Navigate slides", async () => {
    await setupWebsiteBuilder(defaultCarouselMultipleSnippet);
    expect(":iframe .s_carousel_multiple_item:nth-child(1)").toHaveClass("active");
    await contains(":iframe .s_carousel_multiple_item.active").click();

    await contains(".options-container .btn[title='Move Forward']").click();
    await animationFrame();
    expect(":iframe .s_carousel_multiple_item:nth-child(2)").toHaveClass("active");
});

test("Controllers visibility", async () => {
    await setupWebsiteBuilder(defaultCarouselMultipleSnippet, { loadIframeBundles: true });
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
