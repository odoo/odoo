import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { getService } from "@web/../tests/web_test_helpers";

import { registry } from "@web/core/registry";
import { BelowTopFixedElements } from "@website/interactions/below_top_fixed_elements";

class TestBelowTopFixedElements extends BelowTopFixedElements {
    static selector = ".test_below_top_fixed";
    maxHeightGap = 40;

    setup() {
        super.setup();
        this.stickyEl = this.el.querySelectorAll(".test_sticky");
    }
}

beforeEach(() => {
    registry
        .category("public.interactions")
        .add("website.test_below_top_fixed", TestBelowTopFixedElements);
});

setupInteractionWhiteList("website.test_below_top_fixed");

describe.current.tags("interaction_dev");

test("keeps elements below the top fixed elements", async () => {
    const { core } = await startInteractions(`
        <div class="o_top_fixed_element"></div>
        <div class="test_below_top_fixed">
            <div class="test_sticky"></div>
        </div>
    `);
    expect(core.interactions).toHaveLength(1);
    const topFixedEl = queryOne(".o_top_fixed_element");
    const stickyEl = queryOne(".test_sticky");
    const websiteMenus = getService("website_menus");

    topFixedEl.getBoundingClientRect = () => ({ bottom: 70 });
    websiteMenus.triggerCallbacks();
    expect(stickyEl.style.top).toBe("86px");
    expect(stickyEl.style.maxHeight).toBe("calc(-126px + 100vh)");

    topFixedEl.getBoundingClientRect = () => ({ bottom: -10 });
    websiteMenus.triggerCallbacks();
    expect(stickyEl.style.top).toBe("16px");
    expect(stickyEl.style.maxHeight).toBe("calc(-56px + 100vh)");
});

test("reverts the applied style when stopped", async () => {
    const { core } = await startInteractions(`
        <div class="o_top_fixed_element"></div>
        <div class="test_below_top_fixed">
            <div class="test_sticky" style="top: 16px"></div>
        </div>
    `);
    queryOne(".o_top_fixed_element").getBoundingClientRect = () => ({ bottom: 70 });
    getService("website_menus").triggerCallbacks();
    const stickyEl = queryOne(".test_sticky");
    expect(stickyEl.style.top).toBe("86px");

    core.stopInteractions();
    expect(stickyEl.style.top).toBe("16px");
    expect(stickyEl.style.maxHeight).toBe("");
});
