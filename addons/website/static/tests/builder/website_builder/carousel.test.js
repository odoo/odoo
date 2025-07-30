import { expect, test } from "@odoo/hoot";
import { defineWebsiteModels, setupWebsiteBuilder } from "../website_helpers";
import { contains } from "@web/../tests/web_test_helpers";

defineWebsiteModels();

const defaultCarouselStyleSnippet = `
    <section class="s_carousel_wrapper p-0" data-snippet="s_carousel" data-vcss="001">
        <div id="slideshow_sample" class="s_carousel s_carousel_default carousel slide o_colored_level" data-bs-ride="carousel" data-bs-interval="10000">
            <div class="carousel-inner">
                <div class="carousel-item active">
                    <img class="img img-fluid d-block mh-100 mw-100 mx-auto rounded object-fit-cover" src="/web/image/website.library_image_08" data-name="Image" data-index="0" alt=""/>
                </div>
                <div class="carousel-item">
                    <img class="img img-fluid d-block mh-100 mw-100 mx-auto rounded object-fit-cover" src="/web/image/website.library_image_03" data-name="Image" data-index="1" alt=""/>
                </div>
                <div class="carousel-item">
                    <img class="img img-fluid d-block mh-100 mw-100 mx-auto rounded object-fit-cover" src="/web/image/website.library_image_02" data-name="Image" data-index="2" alt=""/>
                </div>
            </div>
            <div class="o_carousel_controllers">
                <button class="carousel-control-prev o_not_editable" contenteditable="false" data-bs-target="#slideshow_sample" data-bs-slide="prev" aria-label="Previous" title="Previous">
                    <span class="carousel-control-prev-icon" aria-hidden="true"/>
                    <span class="visually-hidden">Previous</span>
                </button>
                <div class="carousel-indicators">
                    <button type="button" data-bs-target="#slideshow_sample" data-bs-slide-to="0" style="background-image: url(/web/image/website.library_image_08)" class="active" aria-label="Carousel indicator"/>
                    <button type="button" style="background-image: url(/web/image/website.library_image_03)" data-bs-target="#slideshow_sample" data-bs-slide-to="1" aria-label="Carousel indicator"/>
                    <button type="button" style="background-image: url(/web/image/website.library_image_02)" data-bs-target="#slideshow_sample" data-bs-slide-to="2" aria-label="Carousel indicator"/>
                </div>
                <button class="carousel-control-next o_not_editable" contenteditable="false" data-bs-target="#slideshow_sample" data-bs-slide="next" aria-label="Next" title="Next">
                    <span class="carousel-control-next-icon" aria-hidden="true"/>
                    <span class="visually-hidden">Next</span>
                </button>
            </div>
        </div>
    </section>`;

const imageGalleryCarouselStyleSnippet = `
    <section class="s_image_gallery o_slideshow pt24 pb24 s_image_gallery_controllers_outside s_image_gallery_controllers_outside_arrows_right s_image_gallery_indicators_dots s_image_gallery_arrows_default" data-snippet="s_image_gallery" data-vcss="002" data-columns="3">
        <div class="o_container_small overflow-hidden">
            <div id="slideshow_sample" class="carousel carousel-dark slide" data-bs-ride="carousel" data-bs-interval="10000">
                <div class="carousel-inner">
                    <div class="carousel-item active">
                        <img class="img img-fluid d-block mh-100 mw-100 mx-auto rounded object-fit-cover" src="/web/image/website.library_image_08" data-name="Image" data-index="0" alt=""/>
                    </div>
                    <div class="carousel-item">
                        <img class="img img-fluid d-block mh-100 mw-100 mx-auto rounded object-fit-cover" src="/web/image/website.library_image_03" data-name="Image" data-index="1" alt=""/>
                    </div>
                    <div class="carousel-item">
                        <img class="img img-fluid d-block mh-100 mw-100 mx-auto rounded object-fit-cover" src="/web/image/website.library_image_02" data-name="Image" data-index="2" alt=""/>
                    </div>
                </div>
                <div class="o_carousel_controllers">
                    <button class="carousel-control-prev o_not_editable" contenteditable="false" data-bs-target="#slideshow_sample" data-bs-slide="prev" aria-label="Previous" title="Previous">
                        <span class="carousel-control-prev-icon" aria-hidden="true"/>
                        <span class="visually-hidden">Previous</span>
                    </button>
                    <div class="carousel-indicators">
                        <button type="button" data-bs-target="#slideshow_sample" data-bs-slide-to="0" style="background-image: url(/web/image/website.library_image_08)" class="active" aria-label="Carousel indicator"/>
                        <button type="button" style="background-image: url(/web/image/website.library_image_03)" data-bs-target="#slideshow_sample" data-bs-slide-to="1" aria-label="Carousel indicator"/>
                        <button type="button" style="background-image: url(/web/image/website.library_image_02)" data-bs-target="#slideshow_sample" data-bs-slide-to="2" aria-label="Carousel indicator"/>
                    </div>
                    <button class="carousel-control-next o_not_editable" contenteditable="false" data-bs-target="#slideshow_sample" data-bs-slide="next" aria-label="Next" title="Next">
                        <span class="carousel-control-next-icon" aria-hidden="true"/>
                        <span class="visually-hidden">Next</span>
                    </button>
                </div>
            </div>
        </div>
    </section>`;

test("Test Carousel Option (s_carousel)", async () => {
    const { getEditableContent } = await setupWebsiteBuilder(defaultCarouselStyleSnippet);
    const carouselEl = getEditableContent().querySelector(".carousel");
    await contains(":iframe .carousel").click();

    // Editing the Transition

    await contains(".hb-row[data-label='Transition'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('None')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "carousel");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "10000");

    await contains(".hb-row[data-label='Transition'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('Slide')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "carousel");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "10000");

    await contains(".hb-row[data-label='Transition'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('Fade')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "carousel");
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

test("Test Carousel Option (s_image_gallery)", async () => {
    const { getEditableContent } = await setupWebsiteBuilder(imageGalleryCarouselStyleSnippet);
    const carouselEl = getEditableContent().querySelector(".carousel");
    await contains(":iframe .carousel").click();

    // Editing the Transition

    await contains(".hb-row[data-label='Transition'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('None')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "carousel");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "10000");

    await contains(".hb-row[data-label='Transition'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('Slide')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "carousel");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "10000");

    await contains(".hb-row[data-label='Transition'] button").click();
    await contains(".o-hb-select-dropdown-item:contains('Fade')").click();
    expect(carouselEl).toHaveAttribute("data-bs-ride", "carousel");
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
