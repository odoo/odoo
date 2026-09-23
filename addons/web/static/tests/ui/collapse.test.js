// @ts-check

import { beforeEach, disableAnimations, expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import {
    defineStyle,
    makeMockEnv,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { Collapse } from "@web/ui/collapse/collapse";

beforeEach(async () => {
    disableAnimations();
    await makeMockEnv();
});

class Parent extends Component {
    static components = { Collapse };
    static props = ["*"];
    static template = xml`
        <button class="toggle" t-on-click="() => this.state.open = !this.state.open">Toggle</button>
        <Collapse open="this.state.open" class="'region'">
            <div class="content">body</div>
        </Collapse>
    `;

    setup() {
        this.state = useState({ open: this.props.open ?? false });
    }
}

class TallParent extends Component {
    static components = { Collapse };
    static props = ["*"];
    static template = xml`
        <Collapse open="this.state.open" class="'region'">
            <div class="content" style="height: 200px">body</div>
        </Collapse>
    `;
    setup() {
        this.state = useState({ open: false });
    }
}

test("starts closed", async () => {
    await mountWithCleanup(Parent);

    expect(".region").toHaveClass("collapse");
    expect(".region").not.toHaveClass("show");
    expect(".region").not.toHaveClass("collapsing");
});

test("starts open without playing the opening animation", async () => {
    await mountWithCleanup(Parent, { props: { open: true } });
    await animationFrame();

    expect(".region").toHaveClass("collapse");
    expect(".region").toHaveClass("show");
});

test("opens and closes on toggle", async () => {
    await mountWithCleanup(Parent);

    await click(".toggle");
    await animationFrame();
    expect(".region").toHaveClass("show");
    expect(".region").not.toHaveClass("collapsing");

    await click(".toggle");
    await animationFrame();
    expect(".region").not.toHaveClass("show");
    expect(".region").toHaveClass("collapse");
});

test("leaves no inline sizing behind once settled", async () => {
    await mountWithCleanup(Parent);

    await click(".toggle");
    await animationFrame();

    expect(".region").toHaveAttribute("style", "");
});

test("keeps the slot content mounted while closed", async () => {
    await mountWithCleanup(Parent);

    expect(".content").toHaveCount(1);
});

test("an animation always starts from the size the region currently has", async () => {
    defineStyle(`.collapse:not(.show) { display: none !important; }`);

    /** @type {{ keyframes: any, measured: string }[]} */
    const frames = [];
    patchWithCleanup(Element.prototype, {
        animate(keyframes, options) {
            const el = /** @type {Element} */ (/** @type {any} */ (this));
            frames.push({
                keyframes,
                measured: `${el.getBoundingClientRect().height}px`,
            });
            return super.animate(keyframes, options);
        },
    });

    await mountWithCleanup(TallParent);
    await animationFrame();

    expect(frames.length).toBeGreaterThan(0);
    expect(frames[0].measured).toBe("0px");
    expect(frames[0].keyframes.height[0]).toBe("0px");

    for (const { keyframes, measured } of frames) {
        expect(keyframes.height[0]).toBe(measured);
    }
});
