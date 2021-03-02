/** @odoo-module **/
const { Component, tags } = owl;
import { useService } from "../../src/core/hooks";
import { Registry } from "../../src/core/registry";
import { notificationService } from "../../src/notifications/notification_service";
import { rpcService } from "../../src/services/rpc_service";
import {
  getFixture,
  makeDeferred,
  makeMockXHR,
  makeTestEnv,
  mount,
  nextTick,
} from "../helpers/index";
const { xml } = tags;
let serviceRegistry;
async function testRPC(route, params) {
  let url = "";
  let request;
  let MockXHR = makeMockXHR({ test: true }, function (data) {
    request = data;
    url = this.url;
  });
  const env = await makeTestEnv({
    serviceRegistry,
    browser: { XMLHttpRequest: MockXHR },
  });
  await env.services.rpc(route, params);
  return { url, request };
}
// -----------------------------------------------------------------------------
// Tests
// -----------------------------------------------------------------------------
QUnit.module("RPC", {
  beforeEach() {
    serviceRegistry = new Registry();
    serviceRegistry.add(notificationService.name, notificationService);
    serviceRegistry.add(rpcService.name, rpcService);
  },
});
QUnit.test("can perform a simple rpc", async (assert) => {
  assert.expect(4);
  let MockXHR = makeMockXHR({ result: { action_id: 123 } }, (request) => {
    assert.strictEqual(request.jsonrpc, "2.0");
    assert.strictEqual(request.method, "call");
    assert.ok(typeof request.id === "number");
  });
  const env = await makeTestEnv({
    serviceRegistry,
    browser: { XMLHttpRequest: MockXHR },
  });
  const result = await env.services.rpc("/test/");
  assert.deepEqual(result, { action_id: 123 });
});
QUnit.test("trigger an error when response has 'error' key", async (assert) => {
  assert.expect(1);
  const error = {
    message: "message",
    code: 12,
    data: {
      debug: "data_debug",
      message: "data_message",
    },
  };
  let MockXHR = makeMockXHR({ error });
  const env = await makeTestEnv({
    serviceRegistry,
    browser: { XMLHttpRequest: MockXHR },
  });
  try {
    await env.services.rpc("/test/");
  } catch (error) {
    assert.ok(true);
  }
});
QUnit.test("rpc with simple routes", async (assert) => {
  const info1 = await testRPC("/my/route");
  assert.strictEqual(info1.url, "/my/route");
  const info2 = await testRPC("/my/route", { hey: "there", model: "test" });
  assert.deepEqual(info2.request.params, {
    hey: "there",
    model: "test",
  });
});
QUnit.test("rpc coming from destroyed components are left pending", async (assert) => {
  class MyComponent extends Component {
    constructor() {
      super(...arguments);
      this.rpc = useService("rpc");
    }
  }
  MyComponent.template = xml`<div/>`;
  const def = makeDeferred();
  let MockXHR = makeMockXHR({ result: "1" }, () => {}, def);
  const env = await makeTestEnv({
    serviceRegistry,
    browser: { XMLHttpRequest: MockXHR },
  });
  const component = await mount(MyComponent, { env, target: getFixture() });
  let isResolved = false;
  let isFailed = false;
  component
    .rpc("/my/route")
    .then(() => {
      isResolved = true;
    })
    .catch(() => {
      isFailed = true;
    });
  assert.strictEqual(isResolved, false);
  assert.strictEqual(isFailed, false);
  component.destroy();
  def.resolve();
  await nextTick();
  assert.strictEqual(isResolved, false);
  assert.strictEqual(isFailed, false);
});
QUnit.test("rpc initiated from destroyed components throw exception", async (assert) => {
  assert.expect(1);
  class MyComponent extends Component {
    constructor() {
      super(...arguments);
      this.rpc = useService("rpc");
    }
  }
  MyComponent.template = xml`<div/>`;
  const env = await makeTestEnv({
    serviceRegistry,
  });
  const component = await mount(MyComponent, { env, target: getFixture() });
  component.destroy();
  try {
    await component.rpc("/my/route");
  } catch (e) {
    assert.strictEqual(e.message, "A destroyed component should never initiate a RPC");
  }
});
QUnit.test("check trigger RPC:REQUEST and RPC:RESPONSE for a simple rpc", async (assert) => {
  let MockXHR = makeMockXHR({ test: true }, () => 1);
  const env = await makeTestEnv({
    serviceRegistry,
    browser: { XMLHttpRequest: MockXHR },
  });
  let rpcIdsRequest = [];
  let rpcIdsResponse = [];
  env.bus.on("RPC:REQUEST", null, (rpcId) => {
    rpcIdsRequest.push(rpcId);
    assert.step("RPC:REQUEST");
  });
  env.bus.on("RPC:RESPONSE", null, (rpcId) => {
    rpcIdsResponse.push(rpcId);
    assert.step("RPC:RESPONSE");
  });
  await env.services.rpc("/test/");
  assert.strictEqual(rpcIdsRequest.toString(), rpcIdsResponse.toString());
  assert.verifySteps(["RPC:REQUEST", "RPC:RESPONSE"]);
});
QUnit.test("check trigger RPC:REQUEST and RPC:RESPONSE for a rpc with an error", async (assert) => {
  const error = {
    message: "message",
    code: 12,
    data: {
      debug: "data_debug",
      message: "data_message",
    },
  };
  let MockXHR = makeMockXHR({ error });
  const env = await makeTestEnv({
    serviceRegistry,
    browser: { XMLHttpRequest: MockXHR },
  });
  let rpcIdsRequest = [];
  let rpcIdsResponse = [];
  env.bus.on("RPC:REQUEST", null, (rpcId) => {
    rpcIdsRequest.push(rpcId);
    assert.step("RPC:REQUEST");
  });
  env.bus.on("RPC:RESPONSE", null, (rpcId) => {
    rpcIdsResponse.push(rpcId);
    assert.step("RPC:RESPONSE");
  });
  try {
    await env.services.rpc("/test/");
  } catch (e) {
    assert.ok(true);
  }
  assert.strictEqual(rpcIdsRequest.toString(), rpcIdsResponse.toString());
  assert.verifySteps(["RPC:REQUEST", "RPC:RESPONSE"]);
});
