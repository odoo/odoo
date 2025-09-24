import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { click, queryFirst } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";

setupInteractionWhiteList("website.ripple_effect");

describe.current.tags("interaction_dev");

test("ripple_effect introduces an element on click", async () => {
    const { core } = await startInteractions(`
        <div id="wrapwrap">
            <a class="btn" href="#">Click here</a>
        </div>
    `);
    expect(core.interactions).toHaveLength(1);
    expect(".btn").not.toHaveClass("o_js_ripple_effect");
    expect(queryFirst("span.o_ripple_item")).toBe(null);
    await click(".btn");
    expect(".btn").toHaveClass("o_js_ripple_effect");
    expect(queryFirst("span.o_ripple_item")).not.toBe(null);
    await advanceTime(core.interactions[0].interaction.duration);
    expect(".btn").not.toHaveClass("o_js_ripple_effect");
    expect(queryFirst("span.o_ripple_item")).toBe(null);
    core.stopInteractions();
    expect(core.interactions).toHaveLength(0);
    expect(".btn").not.toHaveClass("o_js_ripple_effect");
    expect(queryFirst("span.o_ripple_item")).toBe(null);
});
