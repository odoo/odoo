/** @odoo-module **/

import { useBus } from "@web/core/bus_hook";
import { makeTestEnv } from "../helpers/mock_env";
import { getFixture, nextTick } from "../helpers/utils";

const { Component, mount, tags } = owl;

QUnit.module("useBus");

QUnit.test("useBus hook: simple usecase", async function (assert) {
    class MyComponent extends Component {
        setup() {
            useBus(this.env.bus, "test-event", this.myCallback);
        }
        myCallback() {
            assert.step("callback");
        }
    }
    MyComponent.template = tags.xml`<div/>`;

    const env = await makeTestEnv();
    const target = getFixture();
    const comp = await mount(MyComponent, { env, target });
    env.bus.trigger("test-event");
    await nextTick();
    assert.verifySteps(["callback"]);

    comp.unmount();
    env.bus.trigger("test-event");
    await nextTick();
    assert.verifySteps([]);

    comp.destroy();
});
