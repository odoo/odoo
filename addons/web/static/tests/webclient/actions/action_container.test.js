// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, onMounted, xml } from "@odoo/owl";
import {
    getMockEnv,
    makeMockEnv,
    mountWithCleanup,
} from "@web/../tests/web_test_helpers";
import { AppEvent } from "@web/core/events";
import { ActionContainer } from "@web/webclient/actions/action_container";

describe.current.tags("desktop");

/** @type {{ mounts: number }} */
let counter;

class TestAction extends Component {
    static template = xml`<div class="o_test_action" t-att-class="this.props.className" t-out="this.props.marker"/>`;
    static props = ["*"];
    setup() {
        onMounted(() => {
            counter.mounts++;
        });
    }
}

class OtherAction extends TestAction {}

async function mountContainer() {
    counter = { mounts: 0 };
    await makeMockEnv();
    return mountWithCleanup(ActionContainer, { noMainContainer: true });
}

async function update(/** @type {any} */ info) {
    getMockEnv().bus.trigger(AppEvent.ACTION_MANAGER_UPDATE, info);
    await animationFrame();
}

test("nothing is rendered until an update arrives", async () => {
    await mountContainer();

    expect(".o_action_manager").toHaveCount(1);
    expect(".o_action_manager").toHaveText("");
    expect(counter.mounts).toBe(0);
});

test("an update renders its component with the given props", async () => {
    await mountContainer();

    await update({
        id: 1,
        Component: TestAction,
        componentProps: { marker: "hello" },
    });

    expect(".o_test_action").toHaveText("hello");
    expect(".o_test_action").toHaveClass("o_action");
    expect(counter.mounts).toBe(1);
});

test("a new id remounts, so the dispatch's onMounted always fires", async () => {
    await mountContainer();

    await update({ id: 1, Component: TestAction, componentProps: { marker: "first" } });
    expect(counter.mounts).toBe(1);

    await update({
        id: 2,
        Component: TestAction,
        componentProps: { marker: "second" },
    });
    expect(".o_test_action").toHaveText("second");
    expect(counter.mounts).toBe(2);
});

test("the same id patches in place rather than remounting", async () => {
    await mountContainer();

    await update({ id: 7, Component: TestAction, componentProps: { marker: "first" } });
    expect(counter.mounts).toBe(1);

    await update({
        id: 7,
        Component: TestAction,
        componentProps: { marker: "second" },
    });
    expect(".o_test_action").toHaveText("second");
    expect(counter.mounts).toBe(1);
});

test("a different component under the same id still remounts", async () => {
    await mountContainer();

    await update({ id: 3, Component: TestAction, componentProps: { marker: "a" } });
    expect(counter.mounts).toBe(1);

    await update({ id: 3, Component: OtherAction, componentProps: { marker: "b" } });
    expect(".o_test_action").toHaveText("b");
    expect(counter.mounts).toBe(2);
});

test("an empty payload clears the screen", async () => {
    await mountContainer();

    await update({ id: 1, Component: TestAction, componentProps: { marker: "x" } });
    expect(".o_test_action").toHaveCount(1);

    await update({});
    expect(".o_action_manager").toHaveText("");
    expect(".o_test_action").toHaveCount(0);
});

test("the bus listener does not outlive the container", async () => {
    const env = await makeMockEnv();
    counter = { mounts: 0 };
    const container = await mountWithCleanup(ActionContainer, {
        noMainContainer: true,
    });

    await update({ id: 1, Component: TestAction, componentProps: { marker: "a" } });
    expect(counter.mounts).toBe(1);

    const infoWhileAlive = container.info;
    container.__owl__.app.destroy();
    env.bus.trigger(AppEvent.ACTION_MANAGER_UPDATE, {
        id: 2,
        Component: TestAction,
        componentProps: { marker: "b" },
    });
    await animationFrame();

    expect(container.info).toBe(infoWhileAlive);
    expect(counter.mounts).toBe(1);
});

test("the ACTION_MANAGER_UPDATE listener is registered in setup, not after mount", async () => {
    const env = await makeMockEnv();
    /** @type {string[]} */
    const registeredBefore = [];
    const realAdd = env.bus.addEventListener.bind(env.bus);
    /** @type {any} */ (env.bus).addEventListener = (
        /** @type {any} */ type,
        /** @type {any} */ listener,
        /** @type {any} */ options,
    ) => {
        registeredBefore.push(type);
        return realAdd(type, listener, options);
    };

    /** @type {string[]} */
    let seenAtMount = [];
    class Probe extends ActionContainer {
        setup() {
            super.setup();
            onMounted(() => {
                seenAtMount = [...registeredBefore];
            });
        }
    }
    await mountWithCleanup(Probe, { env });

    expect(seenAtMount).toInclude(AppEvent.ACTION_MANAGER_UPDATE);
});
