import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { enableTransitions } from "@odoo/hoot-mock";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { contains } from "@web/../tests/web_test_helpers";

setupInteractionWhiteList("website.carousel_multiple");
beforeEach(enableTransitions);

const defaultCarouselMultipleSnippet = `
    <section class="s_carousel_multiple_wrapper pt48 pb48 overflow-hidden" style="--o-carousel-multiple-items-gap: 16px;">
        <div id="myCarousel123" class="s_carousel_multiple s_carousel_default carousel carousel-dark slide container o_displayed_items_4" data-bs-ride="false" data-bs-interval="0" style="--o-carousel-multiple-items: 4;">
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

describe.current.tags("interaction_dev");

const waitForCarouselToSlide = async (carouselEl) =>
    new Promise((resolve) => {
        carouselEl.addEventListener("slid.bs.carousel", resolve, { once: true });
    });

test("can slide through all items with next arrow and loop back to first", async () => {
    await startInteractions(defaultCarouselMultipleSnippet);
    const nextButton = ".carousel-control-next";
    const carouselEl = queryOne(".carousel");
    expect(".s_carousel_multiple").toHaveStyle({ "--o-carousel-multiple-items": "4" });

    // Start at item 1 (active)
    expect(".carousel-item:nth-child(1)").toHaveClass("active");

    // Click next to go to item 2
    await contains(nextButton).click();
    await waitForCarouselToSlide(carouselEl);
    expect(".carousel-item:nth-child(2)").toHaveClass("active");

    // since we display 4 slides, we click next to go to the next element,
    // but we loop back to the first item.
    await contains(nextButton).click();
    await waitForCarouselToSlide(carouselEl);
    await waitForCarouselToSlide(carouselEl);
    expect(".carousel-item:nth-child(1)").toHaveClass("active");
});
