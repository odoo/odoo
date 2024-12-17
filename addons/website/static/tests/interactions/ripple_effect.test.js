import { describe, expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

setupInteractionWhiteList("website.ripple_effect");
describe.current.tags("interaction_dev");

test("ripple effect introduces an element on click", async () => {
    const { core, el } = await startInteractions(`
        <div id="wrapwrap">
            <a class="btn" href="#">Click here</a>
        </div>
    `);
    expect(core.interactions.length).toBe(1);
    const buttonEl = el.querySelector(".btn");
    let rippleEl = buttonEl.querySelector("span.o_ripple_item");
    expect(buttonEl).not.toHaveClass("o_js_ripple_effect");
    expect(rippleEl).toBe(null);
    await click(buttonEl);
    rippleEl = buttonEl.querySelector("span.o_ripple_item");
    expect(buttonEl).toHaveClass("o_js_ripple_effect");
    expect(rippleEl).not.toBe(null);
    await advanceTime(core.interactions[0].interaction.duration);
    expect(buttonEl).not.toHaveClass("o_js_ripple_effect");
    core.stopInteractions();
    expect(core.interactions.length).toBe(0);
    rippleEl = buttonEl.querySelector("span.o_ripple_item");
    expect(rippleEl).toBe(null);
});
