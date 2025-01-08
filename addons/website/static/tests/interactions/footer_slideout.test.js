import { describe, expect, test } from "@odoo/hoot";
import { mockUserAgent } from "@odoo/hoot-mock";
import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

setupInteractionWhiteList("website.footer_slideout");
describe.current.tags("interaction_dev");

test("footer slideout does nothing if the effect is not enabled", async () => {
    const { core } = await startInteractions(`
      <div id="wrapwrap">
          <main style="min-height: 1000px">Stuff</main>
          <footer>Footer stuff</footer>
      </div>
    `);
    expect(core.interactions.length).toBe(0);
});

test("footer slideout only adds a class if the effect is enabled on non-safari", async () => {
    mockUserAgent("android");
    const { core, el } = await startInteractions(`
      <div id="wrapwrap">
          <main style="min-height: 1000px">Stuff</main>
          <footer class="o_footer_slideout">Footer stuff</footer>
      </div>
    `);
    expect(core.interactions.length).toBe(1);
    const wrapEl = el.querySelector("#wrapwrap");
    expect(wrapEl).toHaveClass("o_footer_effect_enable");
});

test("footer slideout adds a class and a pixel if the effect is enabled on safari", async () => {
    mockUserAgent("safari");
    const { core, el } = await startInteractions(`
      <div id="wrapwrap">
          <main style="min-height: 1000px">Stuff</main>
          <footer class="o_footer_slideout">Footer stuff</footer>
      </div>
    `);
    expect(core.interactions.length).toBe(1);
    const wrapEl = el.querySelector("#wrapwrap");
    expect(wrapEl).toHaveClass("o_footer_effect_enable");
    let pixelEl = wrapEl.querySelector(":scope > div");
    expect(pixelEl).not.toBe(null);
    expect(pixelEl.style.width).toBe("1px");
    core.stopInteractions();
    expect(core.interactions.length).toBe(0);
    pixelEl = wrapEl.querySelector(":scope > div");
    expect(pixelEl).toBe(null);
});
