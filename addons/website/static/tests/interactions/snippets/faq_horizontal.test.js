import { expect, test } from "@odoo/hoot";

import { startInteractions, setupInteractionWhiteList } from "../core/helpers";

setupInteractionWhiteList("website.faq_horizontal");

test("faq_horizontal does nothing if there is no .s_faq_horizontal", async () => {
    const { core } = await startInteractions(`
      <div></div>
    `);
    expect(core.interactions.length).toBe(0);
});

test("faq_horizontal activate when there is a .s_faq_horizontal", async () => {
    const { core } = await startInteractions(`
      <section class="s_faq_horizontal"></section>
    `);
    expect(core.interactions.length).toBe(1);
});
