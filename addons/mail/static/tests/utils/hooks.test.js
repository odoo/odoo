// @ts-check
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { useHover, useLongPress } from "@mail/utils/common/hooks";
import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, hover, leave, queryOne, runAllTimers } from "@odoo/hoot-dom";
import { Component, useState, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

function touch(selector, type, { clientX = 0, clientY = 0 } = {}) {
    const ev = Object.assign(new Event(type, { bubbles: true }), {
        touches: [{ clientX, clientY }],
    });
    queryOne(selector).dispatchEvent(ev);
}

class LongPressTarget extends Component {
    static props = [];
    static template = xml`<div class="test-longpress" t-ref="root">press me</div>`;

    setup() {
        useLongPress("root", { action: () => expect.step("long-press") });
    }
}

class LongPressParent extends Component {
    static components = { LongPressTarget };
    static props = [];
    static template = xml`<LongPressTarget t-if="this.state.mounted"/>`;

    setup() {
        this.state = useState({ mounted: true });
    }
}

test("useHover cancels its pending timers on unmount", async () => {
    class HoverTarget extends Component {
        static props = [];
        static template = xml`<div class="test-hover" t-ref="root">hover me</div>`;

        setup() {
            this.hover = useHover("root", {
                onAway: () => expect.step("away"),
                onHovering: [5000, () => expect.step("hovering")],
            });
        }
    }
    class Parent extends Component {
        static components = { HoverTarget };
        static props = [];
        static template = xml`<HoverTarget t-if="this.state.mounted"/>`;

        setup() {
            this.state = useState({ mounted: true });
        }
    }
    const parent = await mountWithCleanup(Parent);
    await hover(".test-hover");
    await leave();
    parent.state.mounted = false;
    await animationFrame();
    await runAllTimers();
    expect.verifySteps([]);
});

test("useLongPress fires its action once the delay elapses", async () => {
    await mountWithCleanup(LongPressParent);
    touch(".test-longpress", "touchstart");
    await runAllTimers();
    expect.verifySteps(["long-press"]);
});

test("useLongPress cancels its pending timer on unmount", async () => {
    const parent = await mountWithCleanup(LongPressParent);
    touch(".test-longpress", "touchstart");
    parent.state.mounted = false;
    await animationFrame();
    await runAllTimers();
    expect.verifySteps([]);
});
