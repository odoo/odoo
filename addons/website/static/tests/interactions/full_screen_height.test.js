import { describe, expect, test } from "@odoo/hoot";
import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

setupInteractionWhiteList("website.full_screen_height");
describe.current.tags("interaction_dev");

test.tags("desktop")("full screen height is not set on visible section", async () => {
    const { core, el } = await startInteractions(`
    <main>
        <section class="o_full_screen_height">content</section>
    </main>
    `);
    expect(core.interactions.length).toBe(1);
    const sectionEl = el.querySelector("section");
    expect(sectionEl.style.minHeight).toBe("");
});

test("full screen height is set on hidden section", async () => {
    const { core, el } = await startInteractions(`
    <main>
        <section class="o_full_screen_height d-none">content</section>
    </main>
    `);
    expect(core.interactions.length).toBe(1);
    const sectionEl = el.querySelector("section");
    expect(sectionEl.getAttribute("style")).toMatch(/min-height: [^;]+ !important/);
    expect(parseInt(sectionEl.style.minHeight)).toBeGreaterThan(1);
    core.stopInteractions();
    expect(core.interactions.length).toBe(0);
    expect(sectionEl.style.minHeight).toBe("");
});
