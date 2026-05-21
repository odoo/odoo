import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { click, queryAll, queryOne } from "@odoo/hoot-dom";
import { enableTransitions } from "@odoo/hoot-mock";

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

test("indicator wrapper click triggers navigation to the correct active slide", async () => {
    const { core } = await startInteractions(`
        <section>
            <div id="carousel_sample" class="carousel carousel-dark" data-bs-ride="false" data-bs-interval="0">
                <div class="carousel-inner">
                    <div class="carousel-item active">
                        <a href="#" class="slide-link position-absolute top-0 start-0 w-100 h-100"></a>
                        <h1>test slide 1</h1>
                    </div>
                    <div class="carousel-item">
                        <h1>test slide 2</h1>
                    </div>
                </div>
                <button class="carousel-control-prev" data-bs-target="#carousel_sample" data-bs-slide="prev" aria-label="Previous" title="Previous">
                    <span class="carousel-control-prev-icon" aria-hidden="true"/>
                    <span class="visually-hidden">Previous</span>
                </button>
                <button class="carousel-control-next" data-bs-target="#carousel_sample" data-bs-slide="next" aria-label="Next" title="Next">
                    <span class="carousel-control-next-icon" aria-hidden="true"/>
                    <span class="visually-hidden">Next</span>
                </button>
                <div class="carousel-indicators">
                    <button type="button" data-bs-target="#carousel_sample" data-bs-slide-to="0" class="active" aria-label="Carousel indicator"/>
                    <button type="button" data-bs-target="#carousel_sample" data-bs-slide-to="1" aria-label="Carousel indicator"/>
                </div>
            </div>
        </section>
    `);
    expect(core.interactions).toHaveLength(1);
    const slideLinkEl = queryOne(".carousel-item.active .slide-link");
    slideLinkEl.addEventListener("click", () => {
        expect.step("slide-click");
    });

    await click(".carousel-indicators");
    expect.verifySteps(["slide-click"]);

    await click(".carousel-indicators button");
    expect.verifySteps([]);

    await click(".carousel-control-next");
    await click(".carousel-indicators");
    expect.verifySteps([]);
});
