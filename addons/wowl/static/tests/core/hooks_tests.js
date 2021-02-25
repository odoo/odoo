/** @odoo-module **/
import { useBus } from "../../src/core/hooks";
import { makeTestEnv, mount, nextTick } from "../helpers";
const { Component, tags } = owl;

QUnit.module("hooks");
QUnit.test("useBus", async function (assert) {
  // The callback should only get called once.
  assert.expect(1);
  class MyComponent extends Component {
    constructor() {
      super(...arguments);
      useBus(this.env.bus, "test-event", this.myCallback);
    }
    myCallback() {
      assert.ok(true);
    }
  }
  MyComponent.template = tags.xml`<div/>`;

  const env = await makeTestEnv();
  const comp = await mount(MyComponent, { env });
  env.bus.trigger("test-event");
  await nextTick();

  comp.unmount();
  env.bus.trigger("test-event");
  await nextTick();
});
