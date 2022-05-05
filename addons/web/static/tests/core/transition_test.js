/** @odoo-module **/

import { Transition, useTransition, config as transitionConfig } from "@web/core/transition";
import { getFixture, mockTimeout, mount, nextTick, patchWithCleanup } from "../helpers/utils";

const { Component, xml, useState } = owl;

QUnit.module("Transition");

QUnit.test("useTransition hook", async (assert) => {
    patchWithCleanup(transitionConfig, {
        disabled: false,
    });
    class Parent extends Component {
        setup() {
            this.transition = useTransition({
                name: "test",
                onLeave: () => assert.step("leave"),
            });
        }
    }
    Parent.template = xml`<div t-if="transition.shouldMount" t-att-class="transition.className"/>`;
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
        setup() {
            this.state = useState({ show: true });
        }
        onLeave() {
            assert.step("leave");
        }
    }
    Parent.template = xml`
        <Transition name="'test'" visible="state.show" t-slot-scope="transition" onLeave="onLeave">
            <div t-att-class="transition.className"/>
        </Transition>
    `;
    Parent.components = { Transition };
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
