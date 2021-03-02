/** @odoo-module **/
import { legacyExtraNextTick, makeTestEnv } from "../helpers/utility";
import { getLegacy } from "wowl.test_legacy";
import { actionRegistry } from "../../src/actions/action_registry";
import { viewRegistry } from "../../src/views/view_registry";
import { createWebClient, doAction, getActionManagerTestConfig } from "./helpers";
let testConfig;
// legacy stuff
let AbstractAction;
let cpHelpers;
let core;
let testUtils;
let Widget;
QUnit.module("ActionManager", (hooks) => {
  hooks.before(() => {
    const legacy = getLegacy();
    AbstractAction = legacy.AbstractAction;
    core = legacy.core;
    testUtils = legacy.testUtils;
    cpHelpers = testUtils.controlPanel;
    Widget = legacy.Widget;
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
  QUnit.module("Misc");
  QUnit.test("can execute actions from id, xmlid and tag", async (assert) => {
    assert.expect(6);
    testConfig.serverData.actions[1] = {
      tag: "client_action_by_db_id",
      target: "main",
      type: "ir.actions.client",
    };
    testConfig.serverData.actions["wowl.some_action"] = {
      tag: "client_action_by_xml_id",
      target: "main",
      type: "ir.actions.client",
    };
    testConfig.actionRegistry
      .add("client_action_by_db_id", () => assert.step("client_action_db_id"))
      .add("client_action_by_xml_id", () => assert.step("client_action_xml_id"))
      .add("client_action_by_object", () => assert.step("client_action_object"));
    const env = await makeTestEnv(testConfig);
    await doAction(env, 1);
    assert.verifySteps(["client_action_db_id"]);
    await doAction(env, "wowl.some_action");
    assert.verifySteps(["client_action_xml_id"]);
    await doAction(env, {
      tag: "client_action_by_object",
      target: "current",
      type: "ir.actions.client",
    });
    assert.verifySteps(["client_action_object"]);
  });
  QUnit.test("no widget memory leaks when doing some action stuff", async function (assert) {
    assert.expect(1);
    let delta = 0;
    testUtils.mock.patch(Widget, {
      init: function () {
        delta++;
        this._super.apply(this, arguments);
      },
      destroy: function () {
        delta--;
        this._super.apply(this, arguments);
      },
    });
    const webClient = await createWebClient({ testConfig });
    await doAction(webClient, 8);
    const n = delta;
    await doAction(webClient, 4);
    // kanban view is loaded, switch to list view
    await cpHelpers.switchView(webClient.el, "list");
    await legacyExtraNextTick();
    // open a record in form view
    await testUtils.dom.click(webClient.el.querySelector(".o_list_view .o_data_row"));
    await legacyExtraNextTick();
    // go back to action 7 in breadcrumbs
    await testUtils.dom.click(webClient.el.querySelector(".o_control_panel .breadcrumb a"));
    await legacyExtraNextTick();
    assert.strictEqual(delta, n, "should have properly destroyed all other widgets");
    webClient.destroy();
    testUtils.mock.unpatch(Widget);
  });
  QUnit.test("no widget memory leaks when executing actions in dialog", async function (assert) {
    assert.expect(1);
    let delta = 0;
    testUtils.mock.patch(Widget, {
      init: function () {
        delta++;
        this._super.apply(this, arguments);
      },
      destroy: function () {
        if (!this.isDestroyed()) {
          delta--;
        }
        this._super.apply(this, arguments);
      },
    });
    const webClient = await createWebClient({ testConfig });
    const n = delta;
    await doAction(webClient, 5);
    await doAction(webClient, { type: "ir.actions.act_window_close" });
    assert.strictEqual(delta, n, "should have properly destroyed all widgets");
    webClient.destroy();
    testUtils.mock.unpatch(Widget);
  });
  QUnit.test("no memory leaks when executing an action while switching view", async function (
    assert
  ) {
    assert.expect(1);
    let def;
    let delta = 0;
    testUtils.mock.patch(Widget, {
      init: function () {
        delta += 1;
        this._super.apply(this, arguments);
      },
      destroy: function () {
        delta -= 1;
        this._super.apply(this, arguments);
      },
    });
    const mockRPC = async function (route, args) {
      if (args && args.method === "read") {
        await Promise.resolve(def);
      }
    };
    const webClient = await createWebClient({ testConfig, mockRPC });
    await doAction(webClient, 4);
    const n = delta;
    await doAction(webClient, 3, { clearBreadcrumbs: true });
    // switch to the form view (this request is blocked)
    def = testUtils.makeTestPromise();
    await testUtils.dom.click(webClient.el.querySelector(".o_list_view .o_data_row"));
    // execute another action meanwhile (don't block this request)
    await doAction(webClient, 4, { clearBreadcrumbs: true });
    // unblock the switch to the form view in action 3
    def.resolve();
    await testUtils.nextTick();
    assert.strictEqual(n, delta, "all widgets of action 3 should have been destroyed");
    webClient.destroy();
    testUtils.mock.unpatch(Widget);
  });
  QUnit.test("no memory leaks when executing an action while loading views", async function (
    assert
  ) {
    assert.expect(1);
    let def;
    let delta = 0;
    testUtils.mock.patch(Widget, {
      init: function () {
        delta += 1;
        this._super.apply(this, arguments);
      },
      destroy: function () {
        delta -= 1;
        this._super.apply(this, arguments);
      },
    });
    const mockRPC = async function (route, args) {
      if (args && args.method === "load_views") {
        await Promise.resolve(def);
      }
    };
    const webClient = await createWebClient({ testConfig, mockRPC });
    // execute action 4 to know the number of widgets it instantiates
    await doAction(webClient, 4);
    const n = delta;
    // execute a first action (its 'load_views' RPC is blocked)
    def = testUtils.makeTestPromise();
    doAction(webClient, 3, { clearBreadcrumbs: true });
    await testUtils.nextTick();
    await legacyExtraNextTick();
    // execute another action meanwhile (and unlock the RPC)
    doAction(webClient, 4, { clearBreadcrumbs: true });
    def.resolve();
    await testUtils.nextTick();
    await legacyExtraNextTick();
    assert.strictEqual(n, delta, "all widgets of action 3 should have been destroyed");
    webClient.destroy();
    testUtils.mock.unpatch(Widget);
  });
  QUnit.test(
    "no memory leaks when executing an action while loading data of default view",
    async function (assert) {
      assert.expect(1);
      let def;
      let delta = 0;
      testUtils.mock.patch(Widget, {
        init: function () {
          delta += 1;
          this._super.apply(this, arguments);
        },
        destroy: function () {
          delta -= 1;
          this._super.apply(this, arguments);
        },
      });
      const mockRPC = async function (route, args) {
        if (route === "/web/dataset/search_read") {
          await Promise.resolve(def);
        }
      };
      const webClient = await createWebClient({ testConfig, mockRPC });
      // execute action 4 to know the number of widgets it instantiates
      await doAction(webClient, 4);
      const n = delta;
      // execute a first action (its 'search_read' RPC is blocked)
      def = testUtils.makeTestPromise();
      doAction(webClient, 3, { clearBreadcrumbs: true });
      await testUtils.nextTick();
      await legacyExtraNextTick();
      // execute another action meanwhile (and unlock the RPC)
      doAction(webClient, 4, { clearBreadcrumbs: true });
      def.resolve();
      await testUtils.nextTick();
      await legacyExtraNextTick();
      assert.strictEqual(n, delta, "all widgets of action 3 should have been destroyed");
      webClient.destroy();
      testUtils.mock.unpatch(Widget);
    }
  );
  QUnit.test('action with "no_breadcrumbs" set to true', async function (assert) {
    assert.expect(2);
    testConfig.serverData.actions[4].context = { no_breadcrumbs: true };
    const webClient = await createWebClient({
      testConfig,
    });
    await doAction(webClient, 3);
    assert.containsOnce(webClient, ".o_control_panel .breadcrumb-item");
    // push another action flagged with 'no_breadcrumbs=true'
    await doAction(webClient, 4);
    assert.containsNone(webClient, ".o_control_panel .breadcrumb-item");
    webClient.destroy();
  });
  QUnit.test("document's title is updated when an action is executed", async function (assert) {
    assert.expect(8);
    const defaultTitle = { zopenerp: "Odoo" };
    const webClient = await createWebClient({ testConfig });
    let currentTitle = webClient.env.services.title.getParts();
    assert.deepEqual(currentTitle, defaultTitle);
    let currentHash = webClient.env.services.router.current.hash;
    assert.deepEqual(currentHash, {});
    await doAction(webClient, 4);
    currentTitle = webClient.env.services.title.getParts();
    assert.deepEqual(currentTitle, {
      ...defaultTitle,
      action: "Partners Action 4",
    });
    currentHash = webClient.env.services.router.current.hash;
    assert.deepEqual(currentHash, { action: "4", model: "partner", view_type: "kanban" });
    await doAction(webClient, 8);
    currentTitle = webClient.env.services.title.getParts();
    assert.deepEqual(currentTitle, {
      ...defaultTitle,
      action: "Favorite Ponies",
    });
    currentHash = webClient.env.services.router.current.hash;
    assert.deepEqual(currentHash, { action: "8", model: "pony", view_type: "list" });
    await testUtils.dom.click($(webClient.el).find("tr.o_data_row:first"));
    await legacyExtraNextTick();
    currentTitle = webClient.env.services.title.getParts();
    assert.deepEqual(currentTitle, {
      ...defaultTitle,
      action: "Twilight Sparkle",
    });
    currentHash = webClient.env.services.router.current.hash;
    assert.deepEqual(currentHash, { action: "8", id: "4", model: "pony", view_type: "form" });
    webClient.destroy();
  });
  QUnit.test("on_reverse_breadcrumb handler is correctly called (legacy)", async function (assert) {
    // This test can be removed as soon as we no longer support legacy actions as the new
    // ActionManager doesn't support this option. Indeed, it is used to reload the previous
    // action when coming back, but we won't need such an artefact to that with Wowl, as the
    // controller will be re-instantiated with an (exported) state given in props.
    assert.expect(5);
    const ClientAction = AbstractAction.extend({
      events: {
        "click button": "_onClick",
      },
      start() {
        this.$el.html('<button class="my_button">Execute another action</button>');
      },
      _onClick() {
        this.do_action(4, {
          on_reverse_breadcrumb: () => assert.step("on_reverse_breadcrumb"),
        });
      },
    });
    core.action_registry.add("ClientAction", ClientAction);
    const webClient = await createWebClient({ testConfig });
    await doAction(webClient, "ClientAction");
    assert.containsOnce(webClient, ".my_button");
    await testUtils.dom.click(webClient.el.querySelector(".my_button"));
    await legacyExtraNextTick();
    assert.containsOnce(webClient, ".o_kanban_view");
    await testUtils.dom.click($(webClient.el).find(".o_control_panel .breadcrumb a:first"));
    await legacyExtraNextTick();
    assert.containsOnce(webClient, ".my_button");
    assert.verifySteps(["on_reverse_breadcrumb"]);
    webClient.destroy();
    delete core.action_registry.map.ClientAction;
  });
  QUnit.test('handles "history_back" event', async function (assert) {
    assert.expect(3);
    const webClient = await createWebClient({ testConfig });
    await doAction(webClient, 4);
    await doAction(webClient, 3);
    assert.containsN(webClient, ".o_control_panel .breadcrumb-item", 2);
    // simulate an "history-back" event
    const ev = new Event("history-back", { bubbles: true, cancelable: true });
    webClient.el.querySelector(".o_view_controller").dispatchEvent(ev);
    await testUtils.nextTick();
    await legacyExtraNextTick();
    assert.containsOnce(webClient, ".o_control_panel .breadcrumb-item");
    assert.strictEqual(
      $(webClient.el).find(".o_control_panel .breadcrumb-item").text(),
      "Partners Action 4",
      "breadcrumbs should display the display_name of the action"
    );
    webClient.destroy();
  });
  QUnit.test("stores and restores scroll position", async function (assert) {
    assert.expect(3);
    for (let i = 0; i < 60; i++) {
      testConfig.serverData.models.partner.records.push({ id: 100 + i, foo: `Record ${i}` });
    }
    const webClient = await createWebClient({ testConfig });
    webClient.el.style.height = "250px";
    // execute a first action
    await doAction(webClient, 3);
    assert.strictEqual(webClient.el.querySelector(".o_content").scrollTop, 0);
    // simulate a scroll
    webClient.el.querySelector(".o_content").scrollTop = 100;
    // execute a second action (in which we don't scroll)
    await doAction(webClient, 4);
    assert.strictEqual(webClient.el.querySelector(".o_content").scrollTop, 0);
    // go back using the breadcrumbs
    await testUtils.dom.click($(webClient.el).find(".o_control_panel .breadcrumb a"));
    await legacyExtraNextTick();
    assert.strictEqual(webClient.el.querySelector(".o_content").scrollTop, 100);
    webClient.destroy();
  });
  QUnit.test('executing an action with target != "new" closes all dialogs', async function (
    assert
  ) {
    assert.expect(4);
    testConfig.serverData.views["partner,false,form"] = `
      <form>
        <field name="o2m">
          <tree><field name="foo"/></tree>
          <form><field name="foo"/></form>
        </field>
      </form>`;
    const webClient = await createWebClient({ testConfig });
    await doAction(webClient, 3);
    assert.containsOnce(webClient, ".o_list_view");
    await testUtils.dom.click($(webClient.el).find(".o_list_view .o_data_row:first"));
    await legacyExtraNextTick();
    assert.containsOnce(webClient, ".o_form_view");
    await testUtils.dom.click($(webClient.el).find(".o_form_view .o_data_row:first"));
    await legacyExtraNextTick();
    assert.containsOnce(document.body, ".modal .o_form_view");
    await doAction(webClient, 1); // target != 'new'
    assert.containsNone(document.body, ".modal");
    webClient.destroy();
  });
  QUnit.test('executing an action with target "new" does not close dialogs', async function (
    assert
  ) {
    assert.expect(4);
    testConfig.serverData.views["partner,false,form"] = `
      <form>
        <field name="o2m">
          <tree><field name="foo"/></tree>
          <form><field name="foo"/></form>
        </field>
      </form>`;
    const webClient = await createWebClient({ testConfig });
    await doAction(webClient, 3);
    assert.containsOnce(webClient, ".o_list_view");
    await testUtils.dom.click($(webClient.el).find(".o_list_view .o_data_row:first"));
    await legacyExtraNextTick();
    assert.containsOnce(webClient, ".o_form_view");
    await testUtils.dom.click($(webClient.el).find(".o_form_view .o_data_row:first"));
    await legacyExtraNextTick();
    assert.containsOnce(document.body, ".modal .o_form_view");
    await doAction(webClient, 5); // target 'new'
    assert.containsN(document.body, ".modal .o_form_view", 2);
    webClient.destroy();
  });
});
