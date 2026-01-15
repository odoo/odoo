import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { queryAll, queryFirst } from "@odoo/hoot-dom";
import { mockUserAgent } from "@odoo/hoot-mock";

setupInteractionWhiteList("website.footer_slideout");

describe.current.tags("interaction_dev");

test("footer_slideout does nothing if the effect is not enabled", async () => {
    const { core } = await startInteractions(`
        <div id="wrapwrap">
            <main style="min-height: 1000px">Main Content</main>
            <footer>Footer Content</footer>
        </div>
    `);
    expect(core.interactions).toHaveLength(0);
});

test("footer_slideout adds a pixel if the effect is enabled on safari", async () => {
    mockUserAgent("safari");
    const { core } = await startInteractions(`
        <div id="wrapwrap">
            <main style="min-height: 1000px">Main Content</main>
            <footer class="o_footer_slideout">Footer Content</footer>
        </div>
    `);
    expect(core.interactions).toHaveLength(1);
    expect(queryAll("#wrapwrap > div")).toHaveLength(1);
    expect("#wrapwrap > div").toHaveStyle({ width: "1px" });
    core.stopInteractions();
    expect(core.interactions).toHaveLength(0);
    expect(queryFirst("#wrapwrap > div")).toBe(null);
});
