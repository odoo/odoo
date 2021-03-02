/** @odoo-module **/
import { legacyExtraNextTick } from "../helpers/utility";
import { getLegacy } from "wowl.test_legacy";
import { actionRegistry } from "../../src/actions/action_registry";
import { viewRegistry } from "../../src/views/view_registry";
import { createWebClient, doAction, getActionManagerTestConfig } from "./helpers";
import { Registry } from "../../src/core/registry";
import { NotificationContainer } from "../../src/notifications/notification_container";
import { DialogContainer } from "../../src/services/dialog_service";
let testConfig;
// legacy stuff
let ListController;
let testUtils;
QUnit.module("ActionManager", (hooks) => {
  hooks.before(() => {
    const legacy = getLegacy();
    ListController = legacy.ListController;
    testUtils = legacy.testUtils;
  });
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

  QUnit.module("Legacy tests (to eventually drop)");

  QUnit.test("display warning as notification", async function (assert) {
    // this test can be removed as soon as the legacy layer is dropped
    assert.expect(5);
    let list;
    testUtils.patch(ListController, {
      init() {
        this._super(...arguments);
        list = this;
      },
    });
    
    const componentRegistry = new Registry();
    componentRegistry.add("NotificationContainer", NotificationContainer)
    testConfig.mainComponentRegistry = componentRegistry;
    const webClient = await createWebClient({ testConfig });
    await doAction(webClient, 3);
    assert.containsOnce(webClient, ".o_list_view");
    list.trigger_up("warning", {
      title: "Warning!!!",
      message: "This is a warning...",
    });
    await testUtils.nextTick();
    await legacyExtraNextTick();
    assert.containsOnce(webClient, ".o_list_view");
    assert.containsOnce(document.body, ".o_notification.bg-warning");
    assert.strictEqual($(".o_notification_title").text(), "Warning!!!");
    assert.strictEqual($(".o_notification_content").text(), "This is a warning...");
    webClient.destroy();
  });
  
  QUnit.test("display warning as modal", async function (assert) {
    // this test can be removed as soon as the legacy layer is dropped
    assert.expect(5);
    let list;
    testUtils.patch(ListController, {
      init() {
        this._super(...arguments);
        list = this;
      },
    });
    const componentRegistry = new Registry();
    componentRegistry.add("DialogContainer", DialogContainer)
    testConfig.mainComponentRegistry = componentRegistry;

    const webClient = await createWebClient({ testConfig });
    await doAction(webClient, 3);
    assert.containsOnce(webClient, ".o_list_view");
    list.trigger_up("warning", {
      title: "Warning!!!",
      message: "This is a warning...",
      type: "dialog",
    });
    await testUtils.nextTick();
    await legacyExtraNextTick();
    assert.containsOnce(webClient, ".o_list_view");
    assert.containsOnce(document.body, ".modal");
    assert.strictEqual($(".modal-title").text(), "Warning!!!");
    assert.strictEqual($(".modal-body").text(), "This is a warning...");
    webClient.destroy();
  });
});
