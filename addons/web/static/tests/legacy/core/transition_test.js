/** @odoo-module alias=@web/../tests/core/transition_test default=false */

import { Transition, useTransition, config as transitionConfig } from "@web/core/transition";
import { getFixture, mockTimeout, mount, nextTick, patchWithCleanup } from "../helpers/utils";

import { Component, xml, useState } from "@odoo/owl";

QUnit.module("Transition");

QUnit.test("useTransition hook", async (assert) => {
    patchWithCleanup(transitionConfig, {
        disabled: false,
    });
    class Parent extends Component {
        static template = xml`<div t-if="transition.shouldMount" t-att-class="transition.className"/>`;
        static props = ["*"];
        setup() {
            this.transition = useTransition({
                name: "test",
                onLeave: () => assert.step("leave"),
            });
        }
    }
    const { execRegisteredTimeouts } = mockTimeout();

    const target = getFixture();
    const parent = await mount(Parent, target);
    // Mounted with -enter but not -enter-active
    assert.containsOnce(target, ".test.test-enter:not(.test-enter-active)");
    await nextTick();
    // No longer has -enter class but now has -enter-active
    assert.containsOnce(target, ".test.test-enter-active:not(.test-enter)");
    parent.transition.shouldMount = false;
    await nextTick();
    // Leaving: -leave but not -enter-active
    assert.containsOnce(target, ".test.test-leave:not(.test-enter-active)");
    assert.verifySteps([]);
    execRegisteredTimeouts();
    assert.verifySteps(["leave"]);
    await nextTick();
    assert.containsNone(target, ".test");
});

QUnit.test("Transition HOC", async (assert) => {
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
            assert.step("leave");
        }
    }
    const { execRegisteredTimeouts } = mockTimeout();

    const target = getFixture();
    const parent = await mount(Parent, target);
    // Mounted with -enter but not -enter-active
    assert.containsOnce(target, ".test.test-enter:not(.test-enter-active)");
    await nextTick();
    // No longer has -enter class but now has -enter-active
    assert.containsOnce(target, ".test.test-enter-active:not(.test-enter)");
    parent.state.show = false;
    await nextTick();
    // Leaving: -leave but not -enter-active
    assert.containsOnce(target, ".test.test-leave:not(.test-enter-active)");
    assert.verifySteps([]);
    execRegisteredTimeouts();
    assert.verifySteps(["leave"]);
    await nextTick();
    assert.containsNone(target, ".test");
});
