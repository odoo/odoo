import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";

import { registry } from "@web/core/registry";
import { StickyBelowHeader } from "@website/interactions/sticky_below_header";

class TestStickyBelowHeader extends StickyBelowHeader {
    static selector = ".test_sticky_below_header";
    maxHeightGap = 40;

    setup() {
        super.setup();
        this.stickyEl = this.el.querySelectorAll(".test_sticky");
    }
}

beforeEach(() => {
    registry
        .category("public.interactions")
        .add("website.test_sticky_below_header", TestStickyBelowHeader);
});

setupInteractionWhiteList("website.test_sticky_below_header");

describe.current.tags("interaction_dev");

test("positions a sticky element below a moving top fixed element", async () => {
    const { core } = await startInteractions(`
        <header class="o_top_fixed_element"></header>
        <div class="test_sticky_below_header">
            <div class="test_sticky"></div>
        </div>
    `);
    expect(core.interactions).toHaveLength(1);
    const interaction = core.interactions[0].interaction;
    const headerEl = queryOne("header");
    headerEl.getBoundingClientRect = () => ({ bottom: 70 });

    interaction.updatePosition();
    const stickyEl = queryOne(".test_sticky");
    expect(stickyEl.style.top).toBe("86px");
    expect(stickyEl.style.maxHeight).toBe("calc(-126px + 100vh)");

    headerEl.getBoundingClientRect = () => ({ bottom: 30 });
    interaction.updatePosition();
    expect(stickyEl.style.top).toBe("46px");
    expect(stickyEl.style.maxHeight).toBe("calc(-86px + 100vh)");

    headerEl.getBoundingClientRect = () => ({ bottom: -10 });
    interaction.updatePosition();
    expect(stickyEl.style.top).toBe("16px");
    expect(stickyEl.style.maxHeight).toBe("calc(-56px + 100vh)");
});

test("positions a sticky element below the lowest top fixed element", async () => {
    const { core } = await startInteractions(`
        <header id="first" class="o_top_fixed_element"></header>
        <header id="second" class="o_top_fixed_element"></header>
        <div class="test_sticky_below_header">
            <div class="test_sticky"></div>
        </div>
    `);
    expect(core.interactions).toHaveLength(1);
    queryOne("#first").getBoundingClientRect = () => ({ bottom: 40 });
    queryOne("#second").getBoundingClientRect = () => ({ bottom: 70 });

    core.interactions[0].interaction.updatePosition();
    const stickyEl = queryOne(".test_sticky");
    expect(stickyEl.style.top).toBe("86px");
    expect(stickyEl.style.maxHeight).toBe("calc(-126px + 100vh)");
});
