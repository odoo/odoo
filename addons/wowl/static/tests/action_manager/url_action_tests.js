/** @odoo-module **/
import { makeTestEnv } from "../helpers/utility";
import { makeFakeRouterService } from "../helpers/mocks";
import { actionRegistry } from "../../src/actions/action_registry";
import { viewRegistry } from "../../src/views/view_registry";
import { doAction, getActionManagerTestConfig } from "./helpers";
let testConfig;
QUnit.module("ActionManager", (hooks) => {
  // Remove this as soon as we drop the legacy support.
  // This is necessary as some tests add actions/views in the legacy registries,
  // which are in turned wrapped and added into the real wowl registries. We
  // add those actions/views in the test registries, and remove them from the
  // real ones (directly, as we don't need them in the test).
  const owner = Symbol("owner");
  hooks.beforeEach(() => {
    actionRegistry.on("UPDATE", owner, (payload) => {
      if (payload.operation === "add" && testConfig.actionRegistry) {
        testConfig.actionRegistry.add(payload.key, payload.value);
        actionRegistry.remove(payload.key);
      }
    });
    viewRegistry.on("UPDATE", owner, (payload) => {
      if (payload.operation === "add" && testConfig.viewRegistry) {
        testConfig.viewRegistry.add(payload.key, payload.value);
        viewRegistry.remove(payload.key);
      }
    });
  });
  hooks.afterEach(() => {
    actionRegistry.off("UPDATE", owner);
    viewRegistry.off("UPDATE", owner);
  });
  hooks.beforeEach(() => {
    testConfig = getActionManagerTestConfig();
  });
  QUnit.module("URL actions");
  QUnit.test("execute an 'ir.actions.act_url' action with target 'self'", async (assert) => {
    var _a;
    (_a = testConfig.serviceRegistry) === null || _a === void 0
      ? void 0
      : _a.add(
          "router",
          makeFakeRouterService({
            redirect: (url) => {
              assert.step(url);
            },
          }),
          true
        );
    const env = await makeTestEnv(testConfig);
    await doAction(env, {
      type: "ir.actions.act_url",
      target: "self",
      url: "/my/test/url",
    });
    assert.verifySteps(["/my/test/url"]);
  });
});
