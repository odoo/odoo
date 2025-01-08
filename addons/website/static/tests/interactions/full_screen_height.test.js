import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";

setupInteractionWhiteList("website.full_screen_height");

describe.current.tags("interaction_dev");

test.tags("desktop")("full_screen_height is not set on visible section", async () => {
    const { core, el } = await startInteractions(`
        <main>
            <section class="o_full_screen_height">content</section>
        </main>
    `);
    expect(core.interactions).toHaveLength(1);
    const sectionEl = el.querySelector("section");
    expect(sectionEl.style.minHeight).toBe("");
});

test("full_screen_height is set on hidden section", async () => {
    const { core, el } = await startInteractions(`
        <main>
            <section class="o_full_screen_height d-none">content</section>
        </main>
    `);
    expect(core.interactions).toHaveLength(1);
    const sectionEl = el.querySelector("section");
    expect(sectionEl.getAttribute("style")).toMatch(/min-height: [^;]+ !important/);
    expect(parseInt(sectionEl.style.minHeight)).toBeGreaterThan(1);
    core.stopInteractions();
    expect(core.interactions).toHaveLength(0);
    expect(sectionEl.style.minHeight).toBe("");
});
