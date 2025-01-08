import {
    isElementInViewport,
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, click, queryAll } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";

setupInteractionWhiteList("website.scroll_button");

describe.current.tags("interaction_dev");

test("scroll button does nothing if there is o_scroll_button", async () => {
    const { core } = await startInteractions(`<div id="wrapwrap"></div>`);
    expect(core.interactions).toHaveLength(0);
});

test("scroll button scrolls to next section", async () => {
    const { core } = await startInteractions(`
        <div id="wrapwrap" style="overflow: scroll; max-height: 500px;">
            <section style="min-height: 500px;">
                <a class="o_scroll_button">First</a>
            </section>
            <section style="min-height: 500px;">
                <a class="o_scroll_button">Second</a>
            </section>
            <section style="min-height: 500px;">
                Third
            </section>
        </div >
    `);
    expect(core.interactions).toHaveLength(2);
    const aEls = queryAll("a");
    const sectionEls = queryAll("section");
    expect(isElementInViewport(sectionEls[0])).toBe(true);
    expect(isElementInViewport(sectionEls[1])).toBe(false);
    expect(isElementInViewport(sectionEls[2])).toBe(false);
    click(aEls[0]);
    expect(isElementInViewport(sectionEls[0])).toBe(true);
    expect(isElementInViewport(sectionEls[1])).toBe(false);
    expect(isElementInViewport(sectionEls[2])).toBe(false);
    await animationFrame();
    await advanceTime(500); // Duration defined in AnchorSlide.
    expect(isElementInViewport(sectionEls[0])).toBe(false);
    expect(isElementInViewport(sectionEls[1])).toBe(true);
    expect(isElementInViewport(sectionEls[2])).toBe(false);
    click(aEls[1]);
    expect(isElementInViewport(sectionEls[0])).toBe(false);
    expect(isElementInViewport(sectionEls[1])).toBe(true);
    expect(isElementInViewport(sectionEls[2])).toBe(false);
    await animationFrame();
    await advanceTime(500); // Duration defined in AnchorSlide.
    expect(isElementInViewport(sectionEls[0])).toBe(false);
    expect(isElementInViewport(sectionEls[1])).toBe(false);
    expect(isElementInViewport(sectionEls[2])).toBe(true);
});
