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
    expect.verifySteps([]);
    await runAllTimers();
    expect.verifySteps(["leave"]);
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
    expect.verifySteps([]);
    await runAllTimers();
    expect.verifySteps(["leave"]);
    await animationFrame();
    expect(".test").toHaveCount(0);
});

test("test transitionWhenMounted attribute in Transition/useTransition", async () => {
    patchWithCleanup(transitionConfig, {
        disabled: false,
    });
    class Parent extends Component {
        static template = xml`
            <Transition name="'test'" visible="state.show" t-slot-scope="transition" onLeave="onLeave" transitionWhenMounted="false">
                <div t-att-class="transition.className" class="hello"/>
            </Transition>
        `;
        static components = { Transition };
        static props = ["*"];
        setup() {
            this.state = useState({ show: false });
        }
        onLeave() {
            expect.step("leave");
        }
    }

    class ParentModified extends Parent {
        setup() {
            this.state = useState({ show: true });
        }
    }

    // Consider Parent as a component which is not visible when component
    // is rendered.
    // Whereas ParentModified is a component which is already mounted when
    // component is rendered or normal component which can stay mounted when
    // switching views or a component which uses Transition and can stay
    // mounted after refreshing.

    // noMainContainer, because the await for the mount of the main container
    // will already change the transition
    const parent = await mountWithCleanup(Parent, { noMainContainer: false });

    parent.state.show = true;

    // Normal Behaviour
    await animationFrame();
    // Mounted with -enter but not -enter-active
    expect(".test.test-enter:not(.test-enter-active)").toHaveCount(1);
    await animationFrame();
    expect(".test.test-enter-active:not(.test-enter)").toHaveCount(1);

    // Consider we did reload here and resulting component to be rendered would be ParentModified
    const parentExtended = await mountWithCleanup(ParentModified, { noMainContainer: false });

    // Comes to skip state as the component is already mounted.
    expect(".test.test-skip:not(.test-enter-active)").toHaveCount(1);

    parentExtended.state.show = false;
    await animationFrame();
    // Leaving: -leave but not -enter-active
    expect(".test.test-leave:not(.test-enter-active)").toHaveCount(1);

    expect.verifySteps([]);
    await runAllTimers();
    expect.verifySteps(["leave"]);
    await animationFrame();
});
