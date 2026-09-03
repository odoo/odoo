import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { getService } from "@web/../tests/web_test_helpers";

setupInteractionWhiteList("website.header_fade_out");

describe.current.tags("interaction_dev");

test("measures the height covered by the lowest top fixed element", async () => {
    await startInteractions(`
        <div id="first" class="o_top_fixed_element"></div>
        <div id="second" class="o_top_fixed_element"></div>
    `);
    queryOne("#first").getBoundingClientRect = () => ({ bottom: 40 });
    queryOne("#second").getBoundingClientRect = () => ({ bottom: 70 });
    const websiteMenus = getService("website_menus");
    const offsets = [];
    websiteMenus.registerCallback((offset) => offsets.push(offset));

    websiteMenus.triggerCallbacks();
    expect(websiteMenus.getTopFixedOffset()).toBe(70);

    // Moved above the viewport (e.g. a hidden header).
    queryOne("#first").getBoundingClientRect = () => ({ bottom: -10 });
    queryOne("#second").getBoundingClientRect = () => ({ bottom: -10 });
    websiteMenus.triggerCallbacks();
    expect(websiteMenus.getTopFixedOffset()).toBe(0);
    expect(offsets).toEqual([70, 0]);
});

test("a fading header covers the page proportionally to its opacity", async () => {
    await startInteractions(`
        <header class="o_header_fade_out" style="opacity: 0.5"></header>
        <main></main>
    `);
    const headerEl = queryOne("header");
    headerEl.getBoundingClientRect = () => ({ bottom: 80, height: 80 });
    const websiteMenus = getService("website_menus");

    websiteMenus.triggerCallbacks();
    expect(websiteMenus.getTopFixedOffset()).toBe(40);

    headerEl.style.opacity = "0";
    websiteMenus.triggerCallbacks();
    expect(websiteMenus.getTopFixedOffset()).toBe(0);

    headerEl.style.opacity = "1";
    websiteMenus.triggerCallbacks();
    expect(websiteMenus.getTopFixedOffset()).toBe(80);
});
