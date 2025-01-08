import { describe, expect, test } from "@odoo/hoot";
import { manuallyDispatchProgrammaticEvent } from "@odoo/hoot-dom";
import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

setupInteractionWhiteList("website.website_animate_overflow");
describe.current.tags("interaction_dev");

test("website animate overflow adds class during animations", async () => {
    const { core, el } = await startInteractions(`
        <div id="wrapwrap">
            <div class="o_animate"/>
        </div>
    `);
    expect(core.interactions.length).toBe(1);
    const htmlEl = el.closest("html");
    expect(htmlEl).not.toHaveClass("o_wanim_overflow_xy_hidden");
    const animatedEl = el.querySelector(".o_animate");
    animatedEl.classList.add("o_animating");
    await manuallyDispatchProgrammaticEvent(animatedEl, "updatecontent");
    expect(htmlEl).toHaveClass("o_wanim_overflow_xy_hidden");
    animatedEl.classList.remove("o_animating");
    await manuallyDispatchProgrammaticEvent(animatedEl, "updatecontent");
    expect(htmlEl).not.toHaveClass("o_wanim_overflow_xy_hidden");
});

test("website animate overflow always adds class if there are transforms", async () => {
    const { core, el } = await startInteractions(`
        <div id="wrapwrap">
            <div class="o_animate" style="transform: translateY(10px)"/>
        </div>
    `);
    expect(core.interactions.length).toBe(1);
    const htmlEl = el.closest("html");
    expect(htmlEl).toHaveClass("o_wanim_overflow_xy_hidden");
});
