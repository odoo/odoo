import { describe, expect, test } from "@odoo/hoot";
import { manuallyDispatchProgrammaticEvent, queryFirst, queryOne } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

setupInteractionWhiteList("website.references_carousel");

describe.current.tags("interaction_dev");

// The snippet stylesheet is not loaded in unit tests: the logo width is set
// inline, standing for the width an image only gets once loaded.
function getTemplate(logoWidth) {
    return /* html */ `
        <section class="s_references_carousel s_references_carousel_direction_left">
            <div class="s_references_carousel_marquee_container" style="display: flex; width: 400px;">
                <div class="s_references_carousel_marquee_item" style="display: flex; flex: 0 0 auto;">
                    <div class="s_references_carousel_item">
                        <img style="display: block; width: ${logoWidth};" alt=""/>
                    </div>
                </div>
            </div>
        </section>
    `;
}

test("the strip is laid out again once a logo is loaded", async () => {
    await startInteractions(getTemplate("0"));
    const containerEl = queryOne(".s_references_carousel_marquee_container");
    // Not loaded yet: the strip has no width to measure.
    expect(containerEl.style.getPropertyValue("--marquee-item-size")).toBe("");
    expect(".s_references_carousel_marquee_item_clone").toHaveCount(0);

    const imgEl = queryOne(".s_references_carousel_item img");
    imgEl.style.width = "100px";
    manuallyDispatchProgrammaticEvent(imgEl, "load");
    await advanceTime(100);

    expect(containerEl.style.getPropertyValue("--marquee-item-size")).toBe("100");
    expect(".s_references_carousel_marquee_item_clone").toHaveCount(9);
});

test("a clone being loaded does not lay the strip out again", async () => {
    await startInteractions(getTemplate("100px"));
    // A layout after the start: the clones it creates are then part of the
    // dynamic content.
    manuallyDispatchProgrammaticEvent(window, "resize");
    await advanceTime(200);

    const cloneImgEl = queryFirst(".s_references_carousel_marquee_item_clone img");
    manuallyDispatchProgrammaticEvent(cloneImgEl, "load");
    await advanceTime(200);
    // Still the same clone: laying the strip out again would have replaced it,
    // and each new clone loading would have started over, endlessly.
    expect(cloneImgEl.isConnected).toBe(true);
});
