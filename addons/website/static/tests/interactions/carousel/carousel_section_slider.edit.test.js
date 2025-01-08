import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";

import { switchToEditMode } from "../../helpers";

setupInteractionWhiteList("website.carousel_section_slider");

describe.current.tags("interaction_dev");

test("carousel_section_slider resets slide to attributes", async () => {
    const { core, el } = await startInteractions(`
        <section>
            <div id="slideshow_sample" class="carousel carousel-dark slide" data-bs-ride="ride" data-bs-interval="0">
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
        </section>
    `, { waitForStart: true, editMode: true });
    await switchToEditMode(core);

    expect(core.interactions).toHaveLength(1);
    const controlEls = el.querySelectorAll(".carousel-control-prev, .carousel-control-next");
    const indicatorEls = el.querySelectorAll(".carousel-indicators > *");
    for (const controlEl of controlEls) {
        expect(controlEl.dataset.bsSlide).toBe(undefined);
    }
    for (const indicatorEl of indicatorEls) {
        expect(indicatorEl.dataset.bsSlideTo).toBe(undefined);
    }

    core.stopInteractions();

    expect(core.interactions).toHaveLength(0);
    for (const controlEl of controlEls) {
        expect(controlEl.dataset.bsSlide).not.toBe(undefined);
    }
    for (const indicatorEl of indicatorEls) {
        expect(indicatorEl.dataset.bsSlideTo).not.toBe(undefined);
    }
});
