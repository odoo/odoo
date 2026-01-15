import {
    isElementVerticallyInViewportOf,
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, click, queryOne } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";

setupInteractionWhiteList("website.anchor_slide");

describe.current.tags("interaction_dev");

test("anchor_slide does nothing if there is no href", async () => {
    const { core } = await startInteractions(`
        <div id="wrapwrap">
            <a id="somewhere"/>
        </div>
    `);
    expect(core.interactions).toHaveLength(0);
});

test("anchor_slide scrolls to targetted location", async () => {
    const { core } = await startInteractions(`
        <div id="wrapwrap" style="overflow: scroll; width: 500px; max-height: 500px;">
            <a href="#target">Click here</a>
            <div style="min-height: 2000px;">Tall stuff</div>
            <div id="target">Target</div>
        </div>
    `);
    const scrollEl = queryOne("#wrapwrap");
    const targetEl = queryOne("div#target");
    expect(core.interactions).toHaveLength(1);
    expect(isElementVerticallyInViewportOf(targetEl, scrollEl)).toBe(false);
    click("a[href]"); // Intentionally not awaited
    expect(isElementVerticallyInViewportOf(targetEl, scrollEl)).toBe(false);
    await animationFrame();
    await advanceTime(500); // Duration defined in AnchorSlide.
    expect(isElementVerticallyInViewportOf(targetEl, scrollEl)).toBe(true);
});

test("without anchor_slide, instantly reach the targetted location", async () => {
    const { core } = await startInteractions(`
        <div id="wrapwrap" style="overflow: scroll; width: 500px; max-height: 100%;">
            <a href="#target">Click here</a>
            <div style="min-height: 2000px;">Tall stuff</div>
            <div id="target">Target</div>
        </div>
    `);
    const scrollEl = queryOne("#wrapwrap");
    const targetEl = queryOne("div#target");
    expect(core.interactions).toHaveLength(1);
    core.stopInteractions();
    expect(core.interactions).toHaveLength(0);
    expect(isElementVerticallyInViewportOf(targetEl, scrollEl)).toBe(false);
    click("a[href]"); // Intentionally not awaited
    await animationFrame();
    expect(isElementVerticallyInViewportOf(targetEl, scrollEl)).toBe(true);
});

test("anchor_slide scrolls to targetted location - with non-ASCII7 characters", async () => {
    const { core } = await startInteractions(`
        <div id="wrapwrap" style="overflow: scroll; width: 500px; max-height: 500px;">
            <a href="#ok%C3%A9%25">Click here</a>
            <div style="min-height: 2000px;">Tall stuff</div>
            <div class="target" id="ok%C3%A9%25"}">Target</div>
        </div>
    `);
    const scrollEl = queryOne("#wrapwrap");
    const targetEl = queryOne("div.target");
    expect(core.interactions).toHaveLength(1);
    expect(isElementVerticallyInViewportOf(targetEl, scrollEl)).toBe(false);
    click("a[href]"); // Intentionally not awaited
    expect(isElementVerticallyInViewportOf(targetEl, scrollEl)).toBe(false);
    await animationFrame();
    await advanceTime(500); // Duration defined in AnchorSlide.
    expect(isElementVerticallyInViewportOf(targetEl, scrollEl)).toBe(true);
});
