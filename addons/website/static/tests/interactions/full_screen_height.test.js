import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";

setupInteractionWhiteList("website.full_screen_height");

describe.current.tags("interaction_dev");

test.tags("desktop");
test("full_screen_height is not set on visible section", async () => {
    const { core } = await startInteractions(`
        <main>
            <section class="o_full_screen_height">content</section>
        </main>
    `);
    expect(core.interactions).toHaveLength(1);
    const sectionEl = queryOne("section");
    expect(sectionEl).not.toHaveAttribute("style");
});

test("full_screen_height is set on hidden section", async () => {
    const { core } = await startInteractions(`
        <main>
            <section class="o_full_screen_height d-none">content</section>
        </main>
    `);
    expect(core.interactions).toHaveLength(1);
    const sectionEl = queryOne("section");
    expect(sectionEl).toHaveAttribute("style", /min-height: [^;]+ !important/);
    expect(parseInt(sectionEl.style.minHeight)).toBeGreaterThan(1);
    core.stopInteractions();
    expect(core.interactions).toHaveLength(0);
    expect(sectionEl).not.toHaveAttribute("style", /min-height:/);
});
