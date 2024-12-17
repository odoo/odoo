import { describe, expect, test } from "@odoo/hoot";
import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

setupInteractionWhiteList("website.carousel_slider");
describe.current.tags("interaction_dev");

test("carousel slider computes maximum height", async () => {
    const { core, el } = await startInteractions(`
    <div id="slideshow_sample" class="carousel carousel-dark slide" data-bs-ride="false" data-bs-interval="0">
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
            <button class="carousel-control-prev o_not_editable" contenteditable="false" t-attf-data-bs-target="#slideshow_sample" data-bs-slide="prev" aria-label="Previous" title="Previous">
                <span class="carousel-control-prev-icon" aria-hidden="true"/>
                <span class="visually-hidden">Previous</span>
            </button>
            <div class="carousel-indicators">
                <button type="button" data-bs-target="#slideshow_sample" data-bs-slide-to="0" style="background-image: url(/web/image/website.library_image_08)" class="active" aria-label="Carousel indicator"/>
                <button type="button" style="background-image: url(/web/image/website.library_image_03)" data-bs-target="#slideshow_sample" data-bs-slide-to="1" aria-label="Carousel indicator"/>
                <button type="button" style="background-image: url(/web/image/website.library_image_02)" data-bs-target="#slideshow_sample" data-bs-slide-to="2" aria-label="Carousel indicator"/>
            </div>
            <button class="carousel-control-next o_not_editable" contenteditable="false" t-attf-data-bs-target="#slideshow_sample" data-bs-slide="next" aria-label="Next" title="Next">
                <span class="carousel-control-next-icon" aria-hidden="true"/>
                <span class="visually-hidden">Next</span>
            </button>
        </div>
    </div>
    `);
    expect(core.interactions.length).toBe(1);
    const itemEls = el.querySelectorAll(".carousel-item");
    const maxHeight = itemEls[0].style.minHeight;
    for (const itemEl of itemEls) {
        expect(itemEl.style.minHeight).toBe(maxHeight);
    }
    core.stopInteractions();
    expect(core.interactions.length).toBe(0);
    for (const itemEl of itemEls) {
        expect(itemEl.style.minHeight).toBe("");
    }
});
