import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";

import { switchToEditMode } from "../../helpers";

setupInteractionWhiteList("website.carousel_bootstrap_upgrade_fix");

describe.current.tags("interaction_dev");

test("[EDIT] carousel_bootstrap_upgrade_fix prevents ride", async () => {
    const { core } = await startInteractions(`
        <section class="s_image_gallery o_slideshow pt24 pb24 s_image_gallery_controllers_outside s_image_gallery_controllers_outside_arrows_right s_image_gallery_indicators_dots s_image_gallery_arrows_default" data-snippet="s_image_gallery" data-vcss="002" data-columns="3">
            <div class="o_container_small overflow-hidden">
                <div id="slideshow_sample" class="carousel carousel-dark slide" data-bs-interval="5000">
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
        </section>
    `);
    expect(core.interactions).toHaveLength(1);
    await switchToEditMode(core);
    const carouselEl = queryOne(".carousel");
    const carouselBS = window.Carousel.getInstance(carouselEl);
    expect(carouselBS._config.ride).toBe(false);
    expect(carouselBS._config.pause).toBe(true);
    expect(carouselEl).toHaveAttribute("data-bs-ride", "carousel");
});
