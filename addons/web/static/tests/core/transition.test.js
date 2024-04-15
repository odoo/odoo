import { test, expect } from "@odoo/hoot";
import { Transition, useTransition, config as transitionConfig } from "@web/core/transition";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";

import { Component, xml, useState } from "@odoo/owl";
import { animationFrame, runAllTimers } from "@odoo/hoot-mock";

test("useTransition hook", async () => {
    patchWithCleanup(transitionConfig, {
        disabled: false,
    });
    class Parent extends Component {
        static template = xml`<div t-if="transition.shouldMount" t-att-class="transition.className"/>`;
        static props = ["*"];
        setup() {
            this.transition = useTransition({
                name: "test",
                onLeave: () => expect.step("leave"),
            });
        }
    }

    // noMainContainer, because the await for the mount of the main container
    // will already change the transition
    const parent = await mountWithCleanup(Parent, { noMainContainer: true });

    // Mounted with -enter but not -enter-active
    expect(".test.test-enter:not(.test-enter-active)").toHaveCount(1);
    await animationFrame();
    // No longer has -enter class but now has -enter-active
    expect(".test.test-enter-active:not(.test-enter)").toHaveCount(1);
    parent.transition.shouldMount = false;
    await animationFrame();

    // Leaving: -leave but not -enter-active
    expect(".test.test-leave:not(.test-enter-active)").toHaveCount(1);
    expect([]).toVerifySteps();
    await runAllTimers();
    expect(["leave"]).toVerifySteps();
    await animationFrame();
    expect(".test").toHaveCount(0);
});

test("Transition HOC", async () => {
    patchWithCleanup(transitionConfig, {
        disabled: false,
    });
    class Parent extends Component {
        static template = xml`
            <Transition name="'test'" visible="state.show" t-slot-scope="transition" onLeave="onLeave">
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

    // noMainContainer, because the await for the mount of the main container
    // will already change the transition
    const parent = await mountWithCleanup(Parent, { noMainContainer: true });

    // Mounted with -enter but not -enter-active
    expect(".test.test-enter:not(.test-enter-active)").toHaveCount(1);
    await animationFrame();
    // No longer has -enter class but now has -enter-active
    expect(".test.test-enter-active:not(.test-enter)").toHaveCount(1);
    parent.state.show = false;
    await animationFrame();

    // Leaving: -leave but not -enter-active
    expect(".test.test-leave:not(.test-enter-active)").toHaveCount(1);
    expect([]).toVerifySteps();
    await runAllTimers();
    expect(["leave"]).toVerifySteps();
    await animationFrame();
    expect(".test").toHaveCount(0);
});
