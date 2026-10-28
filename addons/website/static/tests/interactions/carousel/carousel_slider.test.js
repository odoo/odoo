import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { beforeEach, describe, expect, getFixture, test } from "@odoo/hoot";
import { click, manuallyDispatchProgrammaticEvent, queryAll } from "@odoo/hoot-dom";
import { advanceTime, enableTransitions } from "@odoo/hoot-mock";
import { onceAllImagesLoaded } from "@website/utils/images";
import { defaultCarouselStyleSnippet } from "./carousel_helpers";

setupInteractionWhiteList("website.carousel_slider");
beforeEach(enableTransitions);

describe.current.tags("interaction_dev");

test("carousel_slider updates min height of carousel items", async () => {
    const { core } = await startInteractions(defaultCarouselStyleSnippet("carousel", "1000"));
    await onceAllImagesLoaded(getFixture());
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
