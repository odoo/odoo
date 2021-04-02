/** @odoo-module **/

import { browser as originalBrowser } from "../../src/core/browser";
import { LoadingIndicator } from "../../src/webclient/loading_indicator/loading_indicator";
import { uiService } from "../../src/services/ui_service";
import { Registry } from "../../src/core/registry";
import { getFixture, nextTick } from "../helpers/utils";
import { patch, unpatch } from "../../src/utils/patch";
import { makeTestEnv } from "../helpers/mock_env";

const { mount } = owl;

let target;
let serviceRegistry;
let browser;
let baseConfig;

QUnit.module("LoadingIndicator", {
  async beforeEach() {
    target = getFixture();
    serviceRegistry = new Registry();
    serviceRegistry.add("ui", uiService);
    browser = { setTimeout: () => 1 };
    baseConfig = { serviceRegistry, browser };
  },
});

QUnit.test("displays the loading indicator in non debug mode", async (assert) => {
  const env = await makeTestEnv({ ...baseConfig });
  await mount(LoadingIndicator, { env, target });
  let loadingIndicator = target.querySelector(".o_loading");
  assert.strictEqual(loadingIndicator, null, "the loading indicator should not be displayed");
  env.bus.trigger("RPC:REQUEST", 1);
  await nextTick();
  loadingIndicator = target.querySelector(".o_loading");
  assert.notStrictEqual(loadingIndicator, null, "the loading indicator should be displayed");
  assert.strictEqual(
    loadingIndicator.textContent,
    "Loading",
    "the loading indicator should display 'Loading'"
  );
  env.bus.trigger("RPC:RESPONSE", 1);
  await nextTick();
  loadingIndicator = target.querySelector(".o_loading");
  assert.strictEqual(loadingIndicator, null, "the loading indicator should not be displayed");
});

QUnit.test("displays the loading indicator for one rpc in debug mode", async (assert) => {
  const env = await makeTestEnv(Object.assign(baseConfig, { debug: "1" }));
  await mount(LoadingIndicator, { env, target });
  let loadingIndicator = target.querySelector(".o_loading");
  assert.strictEqual(loadingIndicator, null, "the loading indicator should not be displayed");
  env.bus.trigger("RPC:REQUEST", 1);
  await nextTick();
  loadingIndicator = target.querySelector(".o_loading");
  assert.notStrictEqual(loadingIndicator, null, "the loading indicator should be displayed");
  assert.strictEqual(
    loadingIndicator.textContent,
    "Loading (1)",
    "the loading indicator should indicate 1 request in progress"
  );
  env.bus.trigger("RPC:RESPONSE", 1);
  await nextTick();
  loadingIndicator = target.querySelector(".o_loading");
  assert.strictEqual(loadingIndicator, null, "the loading indicator should not be displayed");
});

QUnit.test("displays the loading indicator for multi rpc in debug mode", async (assert) => {
  const env = await makeTestEnv(Object.assign(baseConfig, { debug: "1" }));
  await mount(LoadingIndicator, { env, target });
  let loadingIndicator = target.querySelector(".o_loading");
  assert.strictEqual(loadingIndicator, null, "the loading indicator should not be displayed");
  env.bus.trigger("RPC:REQUEST", 1);
  env.bus.trigger("RPC:REQUEST", 2);
  await nextTick();
  loadingIndicator = target.querySelector(".o_loading");
  assert.notStrictEqual(loadingIndicator, null, "the loading indicator should be displayed");
  assert.strictEqual(
    loadingIndicator.textContent,
    "Loading (2)",
    "the loading indicator should indicate 2 requests in progress."
  );
  env.bus.trigger("RPC:REQUEST", 3);
  await nextTick();
  loadingIndicator = target.querySelector(".o_loading");
  assert.strictEqual(
    loadingIndicator.textContent,
    "Loading (3)",
    "the loading indicator should indicate 3 requests in progress."
  );
  env.bus.trigger("RPC:RESPONSE", 1);
  await nextTick();
  loadingIndicator = target.querySelector(".o_loading");
  assert.strictEqual(
    loadingIndicator.textContent,
    "Loading (2)",
    "the loading indicator should indicate 2 requests in progress."
  );
  env.bus.trigger("RPC:REQUEST", 4);
  await nextTick();
  loadingIndicator = target.querySelector(".o_loading");
  assert.strictEqual(
    loadingIndicator.textContent,
    "Loading (3)",
    "the loading indicator should indicate 3 requests in progress."
  );
  env.bus.trigger("RPC:RESPONSE", 2);
  env.bus.trigger("RPC:RESPONSE", 3);
  await nextTick();
  loadingIndicator = target.querySelector(".o_loading");
  assert.strictEqual(
    loadingIndicator.textContent,
    "Loading (1)",
    "the loading indicator should indicate 1 request in progress."
  );
  env.bus.trigger("RPC:RESPONSE", 4);
  await nextTick();
  loadingIndicator = target.querySelector(".o_loading");
  assert.strictEqual(loadingIndicator, null, "the loading indicator should not be displayed");
});

QUnit.test("loading indicator blocks UI", async (assert) => {
  const env = await makeTestEnv({ ...baseConfig });
  patch(originalBrowser, "mock.settimeout", {
    setTimeout: (callback, delay) => {
      assert.step(`set timeout ${delay}`);
      callback();
    },
  });
  const ui = env.services.ui;
  ui.bus.on("BLOCK", null, () => {
    assert.step("block");
  });
  ui.bus.on("UNBLOCK", null, () => {
    assert.step("unblock");
  });
  await mount(LoadingIndicator, { env, target });
  env.bus.trigger("RPC:REQUEST", 1);
  await nextTick();
  env.bus.trigger("RPC:RESPONSE", 1);
  await nextTick();
  assert.verifySteps(["set timeout 3000", "block", "unblock"]);
  unpatch(originalBrowser, "mock.settimeout");
});
