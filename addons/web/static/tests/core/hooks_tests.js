/** @odoo-module **/

import { useBus, useService } from "../../src/core/hooks";
import { Registry } from "../../src/core/registry";
import { getFixture, makeTestEnv, nextTick } from "../helpers";

const { Component, mount, tags } = owl;

QUnit.module("hooks");

QUnit.test("useBus", async function (assert) {
  // The callback should only get called once.
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
  comp.destroy();
});

QUnit.test("useService: unavailable service", async function (assert) {
  class MyComponent extends Component {
    setup() {
      useService("toy_service");
    }
  }
  MyComponent.template = tags.xml`<div/>`;

  const env = await makeTestEnv();
  const target = getFixture();
  try {
    const comp = await mount(MyComponent, { env, target });
  } catch (e) {
    assert.strictEqual(e.message, "Service toy_service is not available");
  }
});

QUnit.test("useService: service that returns null", async function (assert) {
  class MyComponent extends Component {
    setup() {
      this.toyService = useService("toy_service");
    }
  }
  MyComponent.template = tags.xml`<div/>`;

  const serviceRegistry = new Registry();
  serviceRegistry.add("toy_service", {
    name: "toy_service",
    deploy: () => {
      return null;
    },
  });

  const env = await makeTestEnv({ serviceRegistry });
  const target = getFixture();

  const comp = await mount(MyComponent, { env, target });
  assert.strictEqual(comp.toyService, null);
  comp.unmount();
});
