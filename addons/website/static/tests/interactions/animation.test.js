import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame, click, queryOne, scroll } from "@odoo/hoot-dom";
import { enableTransitions } from "@odoo/hoot-mock";

setupInteractionWhiteList("website.animation");
beforeEach(enableTransitions);

describe.current.tags("interaction_dev");

test("onAppearance animation starts once visible", async () => {
    const { core } = await startInteractions(`
        <div id="wrapwrap" style="overflow: scroll; max-height: 100%;">
            <a href="#target">Get there</a>
            <div style="min-height: 2000px;">Tall stuff</div>
            <div id="target" class="o_anim_fade_in o_animate" style="min-height: 500px;">Animated</div>
            <div style="min-height: 2000px;">Tall stuff</div>
        </div>
    `);
    expect(core.interactions).toHaveLength(1);
    // Scroll top must be obtained on wrapwrap in test.
    core.interactions[0].interaction.scrollingElement = queryOne("#wrapwrap");
    const animEl = queryOne(".o_animate");
    expect(animEl).toHaveStyle({ visibility: "visible" });
    expect(animEl).toHaveStyle({ animationPlayState: "paused" });
    expect(animEl).not.toHaveClass(["o_animating", "o_animated"]);
    await click("a");
    await animationFrame();
    expect(animEl).toHaveStyle({ animationPlayState: "running" });
    expect(animEl).toHaveClass("o_animating");
    expect(animEl).not.toHaveClass("o_animated");
});

test("on scroll animation changes based on scroll", async () => {
    const { core } = await startInteractions(`
        <div id="wrapwrap" style="overflow: scroll; max-height: 100%;">
            <div style="min-height: 2000px;">Tall stuff</div>
            <div class="o_anim_fade_in o_animate o_animate_on_scroll"
                style="min-height: 500px; animation-duration: 5s"
                data-scroll-zone-start="0"
                data-scroll-zone-end="100">
                Animated
            </div>
            <div style="min-height: 2000px;">Tall stuff</div>
        </div>
    `);
    expect(core.interactions).toHaveLength(1);
    const wrapEl = queryOne("#wrapwrap");
    // Scroll top must be obtained on wrapwrap in test.
    core.interactions[0].interaction.scrollingElement = wrapEl;
    const animEl = queryOne(".o_animate");
    expect(animEl).toHaveStyle({ visibility: "visible" });

    const delay0 = "0s";
    expect(animEl).toHaveStyle({ animationDelay: delay0 });

    await scroll(wrapEl, { y: 2000 });
    await animationFrame();
    expect(animEl).not.toHaveStyle({ animationDelay: delay0 });
    const delay1 = animEl.style.animationDelay;

    await scroll(wrapEl, { y: 2100 });
    await animationFrame();
    expect(animEl).not.toHaveStyle({ animationDelay: delay0 });
    expect(animEl).not.toHaveStyle({ animationDelay: delay1 });
});

test("onAppearance animation in modal starts once visible", async () => {
    const { core } = await startInteractions(`
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
    expect(core.interactions).toHaveLength(1);
    expect(".o_animate").not.toHaveClass("o_animating");
    window.Modal.getOrCreateInstance(queryOne(".modal")).show();
    await animationFrame();
    expect(".o_animate").toHaveClass("o_animating");
});
