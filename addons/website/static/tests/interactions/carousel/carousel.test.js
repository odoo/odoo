import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { describe, expect, test } from "@odoo/hoot";
import { hover, leave, queryOne } from "@odoo/hoot-dom";
import { animationFrame, advanceTime } from "@odoo/hoot-mock";

setupInteractionWhiteList("website.carousel_bootstrap_upgrade_fix");

describe.current.tags("interaction_dev");

const defaultCarouselStyleSnippet = (bsRide, bsInterval) => `
    <section class="s_carousel_wrapper p-0" data-snippet="s_carousel" data-vcss="001">
        <div id="slideshow_sample" class="s_carousel s_carousel_default carousel slide o_colored_level" data-bs-ride="${bsRide}" data-bs-interval="${bsInterval}">
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

const imageGalleryCarouselStyleSnippet = (bsRide, bsInterval) => `
    <section class="s_image_gallery o_slideshow pt24 pb24 s_image_gallery_controllers_outside s_image_gallery_controllers_outside_arrows_right s_image_gallery_indicators_dots s_image_gallery_arrows_default" data-snippet="s_image_gallery" data-vcss="002" data-columns="3">
        <div class="o_container_small overflow-hidden">
            <div id="slideshow_sample" class="carousel carousel-dark slide" data-bs-ride="${bsRide}" data-bs-interval="${bsInterval}">
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

// TODO : Fix this test
// -> It seems like the first slide of the carousel happen after more than 3s
test.skip("Carousel - Autoplay: Always - 3s - s_carousel", async () => {
    const { core } = await startInteractions(defaultCarouselStyleSnippet("carousel", "3000"));
    expect(core.interactions).toHaveLength(1);
    expect(".carousel .carousel-item:nth-child(1)").toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(2)").not.toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(3)").not.toHaveClass("active");
    await advanceTime(3000);
    await animationFrame();
    // We await twice to be sure the next slide is properly active
    await animationFrame();
    expect(".carousel .carousel-item:nth-child(1)").not.toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(2)").toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(3)").not.toHaveClass("active");
});

// TODO : Fix this test
// -> It seems like the first slide of the carousel happen after more than 3s
test.skip("Carousel - Autoplay: Always - 3s - s_image_gallery", async () => {
    const { core } = await startInteractions(imageGalleryCarouselStyleSnippet("carousel", "3000"));
    expect(core.interactions).toHaveLength(1);
    expect(".carousel .carousel-item:nth-child(1)").toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(2)").not.toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(3)").not.toHaveClass("active");
    await advanceTime(3000);
    await animationFrame();
    // We await twice to be sure the next slide is properly active
    await animationFrame();
    expect(".carousel .carousel-item:nth-child(1)").not.toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(2)").toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(3)").not.toHaveClass("active");
});

test.tags("desktop");
test("Carousel - Autoplay: After First Hover - 3s - s_carousel", async () => {
    const { core } = await startInteractions(defaultCarouselStyleSnippet("true", "3000"));
    expect(core.interactions).toHaveLength(1);
    expect(".carousel .carousel-item:nth-child(1)").toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(2)").not.toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(3)").not.toHaveClass("active");
    await advanceTime(3000);
    await animationFrame();
    // We await twice to be sure the carousel did not slide
    await animationFrame();
    expect(".carousel .carousel-item:nth-child(1)").toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(2)").not.toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(3)").not.toHaveClass("active");
    await hover(queryOne(".carousel"));
    await leave(queryOne(".carousel"));
    await advanceTime(3000);
    await animationFrame();
    // We await twice to be sure the next slide is properly active
    await animationFrame();
    expect(".carousel .carousel-item:nth-child(1)").not.toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(2)").toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(3)").not.toHaveClass("active");
});

test.tags("desktop");
test("Carousel - Autoplay: After First Hover - 3s - s_image_gallery", async () => {
    const { core } = await startInteractions(imageGalleryCarouselStyleSnippet("true", "3000"));
    expect(core.interactions).toHaveLength(1);
    expect(".carousel .carousel-item:nth-child(1)").toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(2)").not.toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(3)").not.toHaveClass("active");
    await advanceTime(3000);
    await animationFrame();
    // We await twice to be sure the carousel did not slide
    await animationFrame();
    expect(".carousel .carousel-item:nth-child(1)").toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(2)").not.toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(3)").not.toHaveClass("active");
    await hover(queryOne(".carousel"));
    await leave(queryOne(".carousel"));
    await advanceTime(3000);
    await animationFrame();
    // We await twice to be sure the next slide is properly active
    await animationFrame();
    expect(".carousel .carousel-item:nth-child(1)").not.toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(2)").toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(3)").not.toHaveClass("active");
});

test("Carousel - Autoplay: Never - 3s - s_carousel", async () => {
    const { core } = await startInteractions(defaultCarouselStyleSnippet("false", "3000"));
    expect(core.interactions).toHaveLength(1);
    expect(".carousel .carousel-item:nth-child(1)").toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(2)").not.toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(3)").not.toHaveClass("active");
    await advanceTime(3000);
    await animationFrame();
    // We await twice to be sure the carousel did not slide
    await animationFrame();
    expect(".carousel .carousel-item:nth-child(1)").toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(2)").not.toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(3)").not.toHaveClass("active");
});

test("Carousel - Autoplay: Never - 3s - s_image_gallery", async () => {
    const { core } = await startInteractions(imageGalleryCarouselStyleSnippet("false", "3000"));
    expect(core.interactions).toHaveLength(1);
    expect(".carousel .carousel-item:nth-child(1)").toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(2)").not.toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(3)").not.toHaveClass("active");
    await advanceTime(3000);
    await animationFrame();
    // We await twice to be sure the carousel did not slide
    await animationFrame();
    expect(".carousel .carousel-item:nth-child(1)").toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(2)").not.toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(3)").not.toHaveClass("active");
});
