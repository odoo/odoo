import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, click, scroll } from "@odoo/hoot-dom";
import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

setupInteractionWhiteList("website.animation");
describe.current.tags("interaction_dev");

test("on appearance animation starts once visible", async () => {
    const { core, el } = await startInteractions(`
        <div id="wrapwrap" style="overflow: scroll; max-height: 100%;">
            <a href="#target">Get there</a>
            <div style="min-height: 2000px;">Tall stuff</div>
            <div id="target" class="o_anim_fade_in o_animate" style="min-height: 500px;">Animated</div>
            <div style="min-height: 2000px;">Tall stuff</div>
        </div>
    `);
    expect(core.interactions.length).toBe(1);
    // Scroll top must be obtained on wrapwrap in test.
    core.interactions[0].interaction.scrollingElement = el.querySelector("#wrapwrap");
    const animEl = el.querySelector(".o_animate");
    expect(animEl.style.visibility).toBe("visible");
    expect(animEl.style.animationPlayState).toBe("paused");
    expect(animEl).not.toHaveClass(["o_animating", "o_animated"]);
    await click(el.querySelector("a"));
    await animationFrame();
    expect(animEl.style.animationPlayState).toBe("running");
    expect(animEl).toHaveClass("o_animating");
    expect(animEl).not.toHaveClass("o_animated");
});

test("on scroll animation changes based on scroll", async () => {
    const { core, el } = await startInteractions(`
        <div id="wrapwrap" style="overflow: scroll; max-height: 100%;">
            <div style="min-height: 2000px;">Tall stuff</div>
            <div class="o_anim_fade_in o_animate o_animate_on_scroll" style="min-height: 500px; animation-duration: 5s"
                data-scroll-zone-start="0" data-scroll-zone-end="100"
            >Animated</div>
            <div style="min-height: 2000px;">Tall stuff</div>
        </div>
    `);
    expect(core.interactions.length).toBe(1);
    const wrapEl = el.querySelector("#wrapwrap");
    // Scroll top must be obtained on wrapwrap in test.
    core.interactions[0].interaction.scrollingElement = wrapEl;
    const animEl = el.querySelector(".o_animate");
    expect(animEl.style.visibility).toBe("visible");
    const delay0 = animEl.style.animationDelay;
    expect(delay0).toBe("");
    await scroll(wrapEl, { y: 2000 });
    await animationFrame();
    const delay1 = animEl.style.animationDelay
    expect(delay1).not.toBe("");
    expect(delay1).not.toBe(delay0);
    await scroll(wrapEl, { y: 2100 });
    await animationFrame();
    const delay2 = animEl.style.animationDelay
    expect(delay2).not.toBe("");
    expect(delay2).not.toBe(delay1);
});

test("on appearance animation in modal starts once visible", async () => {
    const { core, el } = await startInteractions(`
        <div id="wrapwrap">
            <div class="modal" style="display: none;" data-show-after="1000" data-display="afterDelay" data-bs-backdrop="false">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="o_anim_fade_in o_animate">Animated</div>
                    </div>
                </div>
            </div>
        </div>
    `);
    expect(core.interactions.length).toBe(1);
    const modalEl = el.querySelector(".modal");
    const animEl = el.querySelector(".o_animate");
    expect(animEl).not.toHaveClass("o_animating");
    window.Modal.getOrCreateInstance(modalEl).show();
    await animationFrame();
    expect(animEl).toHaveClass("o_animating");
});
