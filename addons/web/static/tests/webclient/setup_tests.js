/** @odoo-module **/

import { Registry } from "../../src/core/registry";
import { makeTestEnv } from "../helpers/mock_env";
import { makeDeferred, nextTick } from "../helpers/utils";

let serviceRegistry;

QUnit.module("deployServices", {
  beforeEach() {
    serviceRegistry = new Registry();
  },
});

QUnit.test("can start a service", async (assert) => {
  serviceRegistry.add("test", {
    name: "test",
    start() {
      return 17;
    },
  });
  const env = await makeTestEnv({ serviceRegistry });
  assert.strictEqual(env.services.test, 17);
});

QUnit.test("can start an asynchronous service", async (assert) => {
  const def = makeDeferred();
  serviceRegistry.add("test", {
    name: "test",
    async start() {
      assert.step("before");
      const result = await def;
      assert.step("after");
      return result;
    },
  });
  const prom = makeTestEnv({ serviceRegistry });
  assert.verifySteps(["before"]);
  def.resolve(15);
  const env = await prom;
  assert.verifySteps(["after"]);
  assert.strictEqual(env.services.test, 15);
});

QUnit.test("can start two sequentially dependant asynchronous services", async (assert) => {
  const def1 = makeDeferred();
  const def2 = makeDeferred();
  serviceRegistry.add("test2", {
    dependencies: ["test1"],
    name: "test2",
    start() {
      assert.step("test2");
      return def2;
    },
  });
  serviceRegistry.add("test1", {
    name: "test1",
    start() {
      assert.step("test1");
      return def1;
    },
  });
  serviceRegistry.add("test3", {
    dependencies: ["test2"],
    name: "test3",
    start() {
      assert.step("test3");
    },
  });
  const promise = makeTestEnv({ serviceRegistry });
  await nextTick();
  assert.verifySteps(["test1"]);
  def2.resolve();
  await nextTick();
  assert.verifySteps([]);
  def1.resolve();
  await nextTick();
  assert.verifySteps(["test2", "test3"]);
  await promise;
});

QUnit.test("can start two independant asynchronous services in parallel", async (assert) => {
  const def1 = makeDeferred();
  const def2 = makeDeferred();
  serviceRegistry.add("test1", {
    name: "test1",
    start() {
      assert.step("test1");
      return def1;
    },
  });
  serviceRegistry.add("test2", {
    name: "test2",
    start() {
      assert.step("test2");
      return def2;
    },
  });
  serviceRegistry.add("test3", {
    dependencies: ["test1", "test2"],
    name: "test3",
    start() {
      assert.step("test3");
    },
  });
  const promise = makeTestEnv({ serviceRegistry });
  await nextTick();
  assert.verifySteps(["test1", "test2"]);
  def1.resolve();
  await nextTick();
  assert.verifySteps([]);
  def2.resolve();
  await nextTick();
  assert.verifySteps(["test3"]);
  await promise;
});

QUnit.test("can start a service with a dependency", async (assert) => {
  serviceRegistry.add("aang", {
    dependencies: ["appa"],
    name: "aang",
    start() {
      assert.step("aang");
    },
  });
  serviceRegistry.add("appa", {
    name: "appa",
    start() {
      assert.step("appa");
    },
  });
  await makeTestEnv({ serviceRegistry });
  assert.verifySteps(["appa", "aang"]);
});
