// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { resize } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { getViewportDimensions, useViewportChange } from "@web/core/utils/dom/dvu";

describe.current.tags("desktop");

test("getViewportDimensions: prefers visualViewport when present", () => {
    patchWithCleanup(browser, {
        visualViewport: /** @type {any} */ ({ width: 812, height: 543 }),
        innerWidth: 1000,
        innerHeight: 700,
    });
    expect(getViewportDimensions()).toEqual({ width: 812, height: 543 });
});

test("getViewportDimensions: falls back to innerWidth/innerHeight without visualViewport", () => {
    patchWithCleanup(browser, {
        visualViewport: /** @type {any} */ (undefined),
        innerWidth: 1024,
        innerHeight: 768,
    });
    expect(getViewportDimensions()).toEqual({ width: 1024, height: 768 });
});

test("useViewportChange: fires on viewport change while mounted, stops after unmount", async () => {
    let calls = 0;
    /** @type {{ show: boolean }} */
    let parentState;

    class Child extends Component {
        static template = xml`<div class="child"/>`;
        static props = ["*"];
        setup() {
            useViewportChange(() => {
                calls++;
            });
        }
    }
    class Parent extends Component {
        static components = { Child };
        static template = xml`<Child t-if="this.state.show"/>`;
        static props = ["*"];
        setup() {
            this.state = useState({ show: true });
            parentState = this.state;
        }
    }

    await mountWithCleanup(Parent);

    await resize({ width: 640, height: 480 });
    await animationFrame();
    expect(calls).toBe(1);

    parentState.show = false;
    await animationFrame();
    const callsAtUnmount = calls;

    await resize({ width: 800, height: 600 });
    await animationFrame();
    expect(calls).toBe(callsAtUnmount);
});

test("useViewportChange subscribes lazily and releases with its last consumer", async () => {
    const added = [];
    const removed = [];
    const originalAdd = browser.addEventListener.bind(browser);
    const originalRemove = browser.removeEventListener.bind(browser);
    patchWithCleanup(browser, {
        addEventListener(type, listener, options) {
            added.push(type);
            return originalAdd(type, listener, options);
        },
        removeEventListener(type, listener, options) {
            removed.push(type);
            return originalRemove(type, listener, options);
        },
    });

    let calls = 0;
    class Child extends Component {
        static template = xml`<div class="child"/>`;
        static props = ["*"];
        setup() {
            useViewportChange(() => calls++);
        }
    }
    /** @type {{ show: boolean }} */
    let state;
    class Parent extends Component {
        static components = { Child };
        static template = xml`<Child t-if="this.state.show"/>`;
        static props = ["*"];
        setup() {
            this.state = useState({ show: true });
            state = this.state;
        }
    }

    await mountWithCleanup(Parent);
    expect(added).toInclude("resize");

    await resize({ width: 640, height: 480 });
    await animationFrame();
    expect(calls).toBe(1);

    state.show = false;
    await animationFrame();
    expect(removed).toInclude("resize");

    await resize({ width: 900, height: 700 });
    await animationFrame();
    expect(calls).toBe(1);
});
