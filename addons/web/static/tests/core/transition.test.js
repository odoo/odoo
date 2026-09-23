// @ts-check

import { expect, test } from "@odoo/hoot";
import { advanceTime, animationFrame, runAllTimers } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import {
    config as transitionConfig,
    Transition,
    useTransition,
} from "@web/core/transition";

test("useTransition hook (default params)", async () => {
    patchWithCleanup(transitionConfig, {
        disabled: false,
    });
    class Parent extends Component {
        static template = xml`<div t-if="this.transition.shouldMount" t-att-class="this.transition.className"/>`;
        static props = ["*"];
        setup() {
            this.transition = useTransition({
                name: "test",
                onLeave: () => expect.step("leave"),
            });
        }
    }

    const parent = await mountWithCleanup(Parent, { noMainContainer: true });

    expect(".test.test-enter-active:not(.test-enter)").toHaveCount(1);
    parent.transition.shouldMount = false;
    await animationFrame();

    expect(".test.test-leave:not(.test-enter-active)").toHaveCount(1);
    expect.verifySteps([]);
    await runAllTimers();
    expect.verifySteps(["leave"]);
    await animationFrame();
    expect(".test").toHaveCount(0);
});

test("useTransition hook (initially visible and immediate=true)", async () => {
    patchWithCleanup(transitionConfig, {
        disabled: false,
    });
    class Parent extends Component {
        static template = xml`<div t-if="this.transition.shouldMount" t-att-class="this.transition.className"/>`;
        static props = ["*"];
        setup() {
            this.transition = useTransition({
                name: "test",
                immediate: true,
                onLeave: () => expect.step("leave"),
            });
        }
    }

    const parent = await mountWithCleanup(Parent, { noMainContainer: true });

    expect(".test.test-enter:not(.test-enter-active)").toHaveCount(1);
    await animationFrame();
    expect(".test.test-enter-active:not(.test-enter)").toHaveCount(1);
    parent.transition.shouldMount = false;
    await animationFrame();

    expect(".test.test-leave:not(.test-enter-active)").toHaveCount(1);
    expect.verifySteps([]);
    await runAllTimers();
    expect.verifySteps(["leave"]);
    await animationFrame();
    expect(".test").toHaveCount(0);
});

test("useTransition hook (initially not visible)", async () => {
    patchWithCleanup(transitionConfig, {
        disabled: false,
    });
    class Parent extends Component {
        static template = xml`<div t-if="this.transition.shouldMount" t-att-class="this.transition.className"/>`;
        static props = ["*"];
        setup() {
            this.transition = useTransition({
                name: "test",
                initialVisibility: false,
                onLeave: () => expect.step("leave"),
            });
        }
    }

    const parent = await mountWithCleanup(Parent, { noMainContainer: true });
    expect(".test").toHaveCount(0);

    parent.transition.shouldMount = true;
    await animationFrame();

    expect(".test.test-enter:not(.test-enter-active)").toHaveCount(1);
    await animationFrame();
    expect(".test.test-enter-active:not(.test-enter)").toHaveCount(1);
    await runAllTimers();
    expect.verifySteps([]);
    await animationFrame();
});

test("useTransition hook (initially not visible) does not fire onLeave on init", async () => {
    patchWithCleanup(transitionConfig, {
        disabled: false,
    });
    class Parent extends Component {
        static template = xml`<div t-if="this.transition.shouldMount" t-att-class="this.transition.className"/>`;
        static props = ["*"];
        setup() {
            this.transition = useTransition({
                name: "test",
                initialVisibility: false,
                onLeave: () => expect.step("leave"),
            });
        }
    }

    await mountWithCleanup(Parent, { noMainContainer: true });
    expect(".test").toHaveCount(0);

    await runAllTimers();
    await animationFrame();
    expect(".test").toHaveCount(0);
    expect.verifySteps([]);
});

test("Transition HOC", async () => {
    patchWithCleanup(transitionConfig, {
        disabled: false,
    });
    class Parent extends Component {
        static template = xml`
            <Transition name="'test'" visible="this.state.show" immediate="true" t-slot-scope="transition" onLeave="this.onLeave">
                <div t-att-class="transition.className"/>
            </Transition>
        `;
        static components = { Transition };
        static props = ["*"];
        setup() {
            this.state = useState({ show: true });
        }
        onLeave() {
            expect.step("leave");
        }
    }

    const parent = await mountWithCleanup(Parent, { noMainContainer: true });

    expect(".test.test-enter:not(.test-enter-active)").toHaveCount(1);
    await animationFrame();
    expect(".test.test-enter-active:not(.test-enter)").toHaveCount(1);
    parent.state.show = false;
    await animationFrame();

    expect(".test.test-leave:not(.test-enter-active)").toHaveCount(1);
    expect.verifySteps([]);
    await runAllTimers();
    expect.verifySteps(["leave"]);
    await animationFrame();
    expect(".test").toHaveCount(0);
});

test("name and leaveDuration follow the props that carry them", async () => {
    class Parent extends Component {
        static components = { Transition };
        static template = xml`
            <Transition name="this.state.name" visible="this.state.visible" leaveDuration="this.state.leaveDuration" t-slot-scope="transition">
                <div class="target" t-att-class="transition.className"/>
            </Transition>`;
        /** @type {string[]} */
        static props = [];
        state = useState({ name: "first", visible: true, leaveDuration: 1000 });
    }
    const parent = await mountWithCleanup(Parent);
    expect(".target").toHaveClass("first-enter-active");

    parent.state.name = "second";
    await animationFrame();
    expect(".target").toHaveClass("second-enter-active");
    expect(".target").not.toHaveClass("first-enter-active");

    parent.state.leaveDuration = 50;
    parent.state.visible = false;
    await animationFrame();
    expect(".target").toHaveClass("second-leave");
    await advanceTime(60);
    await animationFrame();
    expect(".target").toHaveCount(0);
});
