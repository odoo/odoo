import { describe, expect, test } from "@odoo/hoot";

import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";

setupInteractionWhiteList("website.plausible_push");
describe.current.tags("interaction_dev");

test("plausible push does nothing if there is no .js_plausible_push", async () => {
    const { core } = await startInteractions(`
      <div id="wrapwrap">
        <input type='hidden' data-event-name='Lead Generation' data-event-params='{"CTA": "Contact Us"}' />
      </div>`);
    expect(core.interactions.length).toBe(0);
});

test("plausible push interaction notifies plausible if .js_plausible_push", async () => {
    expect(window.plausible).toBe(undefined);
    const { core } = await startInteractions(`
        <div id="wrapwrap">
        <input type='hidden' class='js_plausible_push' data-event-name='Lead Generation' data-event-params='{"CTA": "Contact Us"}' />
        </div>`);
    expect(core.interactions.length).toBe(1);
    expect(window.plausible.q[0][0]).toBe("Lead Generation");
    expect(window.plausible.q[0][1]).toEqual({ props: '{"CTA": "Contact Us"}' });
});
