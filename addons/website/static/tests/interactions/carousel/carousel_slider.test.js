import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { click, manuallyDispatchProgrammaticEvent, queryAll } from "@odoo/hoot-dom";
import { advanceTime, enableTransitions } from "@odoo/hoot-mock";

setupInteractionWhiteList("website.carousel_slider");
beforeEach(enableTransitions);

describe.current.tags("interaction_dev");

test("carousel_slider updates min height of carousel items", async () => {
    const { core } = await startInteractions(`
        <section>
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
        </section>
    `);
    const itemEls = queryAll(".carousel-item");
    const minHeight = itemEls[0].style.minHeight;

    expect(core.interactions).toHaveLength(1);
    for (const itemEl of itemEls) {
        expect(itemEl).toHaveStyle({ minHeight });
    }

    core.stopInteractions();

    expect(core.interactions).toHaveLength(0);
    for (const itemEl of itemEls) {
        expect(itemEl).not.toHaveStyle({ minHeight });
    }
});

test("carousel_slider waits for the end of the slide to update min height", async () => {
    await startInteractions(`
        <div id="slideshow_sample" class="carousel slide" data-bs-ride="false" data-bs-interval="0">
            <div class="carousel-inner">
                <div class="carousel-item active"><div style="height: 100px;"><img/></div></div>
                <div class="carousel-item"><div style="height: 100px;"><img/></div></div>
                <div class="carousel-item"><div style="height: 100px;"><img/></div></div>
            </div>
            <button class="carousel-control-next" data-bs-target="#slideshow_sample" data-bs-slide="next"/>
        </div>
    `);
    const itemEls = queryAll(".carousel-item");

    await click(".carousel-control-next");
    expect(".carousel-item-next").toHaveCount(1);

    // An image loading during the slide must not recompute the min height,
    // as measuring the items would cancel the running transitions.
    const imgWrapperEl = itemEls[2].firstElementChild;
    imgWrapperEl.style.height = "200px";
    await manuallyDispatchProgrammaticEvent(imgWrapperEl.querySelector("img"), "load");
    for (const itemEl of itemEls) {
        expect(itemEl).toHaveStyle({ minHeight: "100px" });
    }

    await advanceTime(1000); // Slide duration.
    expect(".carousel-item-next").toHaveCount(0);
    for (const itemEl of itemEls) {
        expect(itemEl).toHaveStyle({ minHeight: "200px" });
    }
});
