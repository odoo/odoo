/** @odoo-module **/

import { useBus } from "../../src/core/hooks";
import { getFixture, makeTestEnv, nextTick } from "../helpers";

const { Component, mount, tags } = owl;

QUnit.module("hooks");

QUnit.test("useBus", async function (assert) {
  // The callback should only get called once.
  assert.expect(1);
  class MyComponent extends Component {
    setup() {
      useBus(this.env.bus, "test-event", this.myCallback);
    }
    myCallback() {
      assert.ok(true);
    }
  }
  MyComponent.template = tags.xml`<div/>`;

  const env = await makeTestEnv();
  const target = getFixture();
  const comp = await mount(MyComponent, { env, target });
  env.bus.trigger("test-event");
  await nextTick();

  comp.unmount();
  env.bus.trigger("test-event");
  await nextTick();
});
