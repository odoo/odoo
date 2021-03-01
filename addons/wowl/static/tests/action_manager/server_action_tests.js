/** @odoo-module **/
import { actionRegistry } from "../../src/actions/action_registry";
import { viewRegistry } from "../../src/views/view_registry";
import { createWebClient, doAction, getActionManagerTestConfig } from "./helpers";
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
  QUnit.module("Server actions");
  QUnit.test("can execute server actions from db ID", async function (assert) {
    assert.expect(10);
    const mockRPC = async (route, args) => {
      assert.step((args && args.method) || route);
      if (route === "/web/action/run") {
        assert.strictEqual(args.action_id, 2, "should call the correct server action");
        return Promise.resolve(1); // execute action 1
      }
    };
    const webClient = await createWebClient({ testConfig, mockRPC });
    await doAction(webClient, 2);
    assert.containsOnce(webClient, ".o_control_panel", "should have rendered a control panel");
    assert.containsOnce(webClient, ".o_kanban_view", "should have rendered a kanban view");
    assert.verifySteps([
      "/wowl/load_menus",
      "/web/action/load",
      "/web/action/run",
      "/web/action/load",
      "load_views",
      "/web/dataset/search_read",
    ]);
    webClient.destroy();
  });
  QUnit.test("handle server actions returning false", async function (assert) {
    assert.expect(10);
    const mockRPC = async (route, args) => {
      assert.step((args && args.method) || route);
      if (route === "/web/action/run") {
        return Promise.resolve(false);
      }
    };
    const webClient = await createWebClient({ testConfig, mockRPC });
    // execute an action in target="new"
    function onClose() {
      assert.step("close handler");
    }
    await doAction(webClient, 5, { onClose });
    assert.containsOnce(
      document.body,
      ".o_technical_modal .o_form_view",
      "should have rendered a form view in a modal"
    );
    // execute a server action that returns false
    await doAction(webClient, 2);
    assert.containsNone(document.body, ".o_technical_modal", "should have closed the modal");
    assert.verifySteps([
      "/wowl/load_menus",
      "/web/action/load",
      "load_views",
      "onchange",
      "/web/action/load",
      "/web/action/run",
      "close handler",
    ]);
    webClient.destroy();
  });
});
