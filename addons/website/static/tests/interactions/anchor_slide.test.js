import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, click } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import {
    isElementInViewport,
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

setupInteractionWhiteList("website.anchor_slide");
describe.current.tags("interaction_dev");

test("anchor slide does nothing if there is no href", async () => {
    const { core } = await startInteractions(`
      <div id="wrapwrap">
        <a id="somewhere" />
      </div>
    `);
    expect(core.interactions.length).toBe(0);
});

test("anchor slide scrolls to targetted location", async () => {
    const { core, el } = await startInteractions(`
        <div id="wrapwrap" style="overflow: scroll; max-height: 500px;">
            <a href="#target">Click here</a>
            <div style="min-height: 2000px;">Tall stuff</div>
            <div id="target">Target</div>
        </div>
    `);
    expect(core.interactions.length).toBe(1);
    const aEl = el.querySelector("a[href]");
    const targetEl = el.querySelector("div#target");
    expect(isElementInViewport(targetEl)).toBe(false);
    click(aEl);
    expect(isElementInViewport(targetEl)).toBe(false);
    await animationFrame();
    await advanceTime(500); // Duration defined in AnchorSlide.
    expect(isElementInViewport(targetEl)).toBe(true);
});

test("without anchor slide instantly reach the targetted location", async () => {
    const { core, el } = await startInteractions(`
        <div id="wrapwrap" style="overflow: scroll; max-height: 100%;">
            <a href="#target">Click here</a>
            <div style="min-height: 2000px;">Tall stuff</div>
            <div id="target">Target</div>
        </div>
    `);
    expect(core.interactions.length).toBe(1);
    core.stopInteractions();
    expect(core.interactions.length).toBe(0);
    const aEl = el.querySelector("a[href]");
    const targetEl = el.querySelector("div#target");
    expect(isElementInViewport(targetEl)).toBe(false);
    click(aEl);
    await animationFrame();
    expect(isElementInViewport(targetEl)).toBe(true);
});

test("anchor slide scrolls to targetted location - with non-ASCII7 characters", async () => {
    const { core, el } = await startInteractions(`
        <div id="wrapwrap" style="overflow: scroll; max-height: 500px;">
            <a href="#ok%C3%A9%25">Click here</a>
            <div style="min-height: 2000px;">Tall stuff</div>
            <div class="target" id="ok%C3%A9%25"}">Target</div>
        </div>
    `);
    expect(core.interactions.length).toBe(1);
    const aEl = el.querySelector("a[href]");
    const targetEl = el.querySelector("div.target");
    expect(isElementInViewport(targetEl)).toBe(false);
    click(aEl);
    expect(isElementInViewport(targetEl)).toBe(false);
    await animationFrame();
    await advanceTime(500); // Duration defined in AnchorSlide.
    expect(isElementInViewport(targetEl)).toBe(true);
});
