/** @odoo-module **/
import { nextTick } from "../helpers/index";
import { legacyExtraNextTick } from "../helpers/utility";
import { getLegacy } from "wowl.test_legacy";
import { actionRegistry } from "../../src/actions/action_registry";
import { viewRegistry } from "../../src/views/view_registry";
import { createWebClient, doAction, getActionManagerTestConfig } from "./helpers";
let testConfig;
// legacy stuff
let testUtils;
QUnit.module("ActionManager", (hooks) => {
  hooks.before(() => {
    const legacy = getLegacy();
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
  QUnit.module('"ir.actions.act_window_close" actions');
  QUnit.test("close the currently opened dialog", async function (assert) {
    assert.expect(2);
    const webClient = await createWebClient({ testConfig });
    // execute an action in target="new"
    await doAction(webClient, 5);
    assert.containsOnce(
      document.body,
      ".o_technical_modal .o_form_view",
      "should have rendered a form view in a modal"
    );
    // execute an 'ir.actions.act_window_close' action
    await doAction(webClient, {
      type: "ir.actions.act_window_close",
    });
    assert.containsNone(document.body, ".o_technical_modal", "should have closed the modal");
    webClient.destroy();
  });
  QUnit.test('execute "on_close" only if there is no dialog to close', async function (assert) {
    assert.expect(3);
    const webClient = await createWebClient({ testConfig });
    // execute an action in target="new"
    await doAction(webClient, 5);
    function onClose() {
      assert.step("on_close");
    }
    const options = { onClose };
    // execute an 'ir.actions.act_window_close' action
    // should not call 'on_close' as there is a dialog to close
    await doAction(webClient, { type: "ir.actions.act_window_close" }, options);
    assert.verifySteps([]);
    // execute again an 'ir.actions.act_window_close' action
    // should call 'on_close' as there is no dialog to close
    await doAction(webClient, { type: "ir.actions.act_window_close" }, options);
    assert.verifySteps(["on_close"]);
    webClient.destroy();
  });
  QUnit.test("close action with provided infos", async function (assert) {
    assert.expect(1);
    const webClient = await createWebClient({ testConfig });
    const options = {
      onClose: function (infos) {
        assert.strictEqual(infos, "just for testing", "should have the correct close infos");
      },
    };
    await doAction(
      webClient,
      {
        type: "ir.actions.act_window_close",
        infos: "just for testing",
      },
      options
    );
    webClient.destroy();
  });
  QUnit.test("history back calls on_close handler of dialog action", async function (assert) {
    assert.expect(4);
    const webClient = await createWebClient({ testConfig });
    function onClose() {
      assert.step("on_close");
    }
    // open a new dialog form
    await doAction(webClient, 5, { onClose });
    assert.containsOnce(webClient.el, ".modal");
    const ev = new Event("history-back", { bubbles: true, cancelable: true });
    webClient.el.querySelector(".o_view_controller").dispatchEvent(ev);
    assert.verifySteps(["on_close"], "should have called the on_close handler");
    await nextTick();
    assert.containsNone(webClient.el, ".modal");
    webClient.destroy();
  });
  QUnit.test(
    "history back calls on_close handler of dialog action with 2 breadcrumbs",
    async function (assert) {
      assert.expect(7);
      const webClient = await createWebClient({ testConfig });
      await doAction(webClient, 1); // kanban
      await doAction(webClient, 3); // list
      assert.containsOnce(webClient.el, ".o_list_view");
      function onClose() {
        assert.step("on_close");
      }
      // open a new dialog form
      await doAction(webClient, 5, { onClose });
      assert.containsOnce(webClient.el, ".modal");
      assert.containsOnce(webClient.el, ".o_list_view");
      const ev = new Event("history-back", { bubbles: true, cancelable: true });
      webClient.el.querySelector(".o_view_controller").dispatchEvent(ev);
      assert.verifySteps(["on_close"], "should have called the on_close handler");
      await nextTick();
      await legacyExtraNextTick();
      assert.containsOnce(webClient.el, ".o_list_view");
      assert.containsNone(webClient.el, ".modal");
      webClient.destroy();
    }
  );
  QUnit.test("web client is not deadlocked when a view crashes", async function (assert) {
    assert.expect(3);
    const readOnFirstRecordDef = testUtils.makeTestPromise();
    const mockRPC = (route, args) => {
      if (args.method === "read" && args.args[0][0] === 1) {
        return readOnFirstRecordDef;
      }
    };
    const webClient = await createWebClient({ testConfig, mockRPC });
    await doAction(webClient, 3);
    // open first record in form view. this will crash and will not
    // display a form view
    await testUtils.dom.click($(webClient.el).find(".o_list_view .o_data_row:first"));
    await legacyExtraNextTick();
    readOnFirstRecordDef.reject("not working as intended");
    await nextTick();
    assert.containsOnce(webClient, ".o_list_view", "there should still be a list view in dom");
    // open another record, the read will not crash
    await testUtils.dom.click($(webClient.el).find(".o_list_view .o_data_row:eq(2)"));
    await legacyExtraNextTick();
    assert.containsNone(webClient, ".o_list_view", "there should not be a list view in dom");
    assert.containsOnce(webClient, ".o_form_view", "there should be a form view in dom");
    webClient.destroy();
  });
});
