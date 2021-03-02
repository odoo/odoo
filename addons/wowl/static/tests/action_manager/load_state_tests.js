/** @odoo-module **/
import { legacyExtraNextTick } from "../helpers/utility";
const { Component, tags } = owl;
import { makeFakeRouterService } from "../helpers/mocks";
import { getLegacy } from "wowl.test_legacy";
import { actionRegistry } from "../../src/actions/action_registry";
import { viewRegistry } from "../../src/views/view_registry";
import { createWebClient, doAction, getActionManagerTestConfig, loadState } from "./helpers";
let testConfig;
// legacy stuff
let AbstractAction;
let core;
let testUtils;
QUnit.module("ActionManager", (hooks) => {
  hooks.before(() => {
    const legacy = getLegacy();
    AbstractAction = legacy.AbstractAction;
    core = legacy.core;
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
  QUnit.module("Load State");
  QUnit.test("action loading", async (assert) => {
    assert.expect(2);
    const webClient = await createWebClient({ testConfig });
    await loadState(webClient, {
      action: "1001",
    });
    assert.containsOnce(webClient, ".test_client_action");
    assert.strictEqual(webClient.el.querySelector(".o_menu_brand").textContent, "App1");
    webClient.destroy();
  });
  QUnit.test("menu loading", async (assert) => {
    assert.expect(2);
    const webClient = await createWebClient({ testConfig });
    await loadState(webClient, {
      menu_id: "2",
    });
    assert.strictEqual(
      webClient.el.querySelector(".test_client_action").textContent.trim(),
      "ClientAction_Id 2"
    );
    assert.strictEqual(webClient.el.querySelector(".o_menu_brand").textContent, "App2");
    webClient.destroy();
  });
  QUnit.test("action and menu loading", async (assert) => {
    assert.expect(2);
    const webClient = await createWebClient({ testConfig });
    await loadState(webClient, {
      action: "1001",
      menu_id: "2",
    });
    assert.strictEqual(
      webClient.el.querySelector(".test_client_action").textContent.trim(),
      "ClientAction_Id 1"
    );
    assert.strictEqual(webClient.el.querySelector(".o_menu_brand").textContent, "App2");
    webClient.destroy();
  });
  QUnit.test("supports action as xmlId", async (assert) => {
    assert.expect(2);
    const webClient = await createWebClient({ testConfig });
    await loadState(webClient, {
      action: "wowl.client_action",
    });
    assert.strictEqual(
      webClient.el.querySelector(".test_client_action").textContent.trim(),
      "ClientAction_xmlId"
    );
    assert.containsNone(webClient, ".o_menu_brand");
    webClient.destroy();
  });
  QUnit.test("supports opening action in dialog", async (assert) => {
    assert.expect(3);
    testConfig.serverData.actions["wowl.client_action"].target = "new";
    const webClient = await createWebClient({ testConfig });
    await loadState(webClient, {
      action: "wowl.client_action",
    });
    assert.containsOnce(webClient, ".test_client_action");
    assert.containsOnce(webClient, ".modal .test_client_action");
    assert.containsNone(webClient, ".o_menu_brand");
    webClient.destroy();
  });
  QUnit.test("should not crash on invalid state", async function (assert) {
    assert.expect(3);
    const mockRPC = async function (route, args) {
      assert.step((args && args.method) || route);
    };
    const webClient = await createWebClient({ testConfig, mockRPC });
    await loadState(webClient, {
      res_model: "partner",
    });
    assert.strictEqual($(webClient.el).text(), "", "should display nothing");
    assert.verifySteps(["/wowl/load_menus"]);
    webClient.destroy();
  });
  QUnit.test("properly load client actions", async function (assert) {
    assert.expect(3);
    class ClientAction extends Component {}
    ClientAction.template = tags.xml`<div class="o_client_action_test">Hello World</div>`;
    testConfig.actionRegistry.add("HelloWorldTest", ClientAction);
    const mockRPC = async function (route, args) {
      assert.step((args && args.method) || route);
    };
    const webClient = await createWebClient({ testConfig, mockRPC });
    webClient.env.bus.trigger("test:hashchange", {
      action: "HelloWorldTest",
    });
    await testUtils.nextTick();
    assert.strictEqual(
      $(webClient.el).find(".o_client_action_test").text(),
      "Hello World",
      "should have correctly rendered the client action"
    );
    assert.verifySteps(["/wowl/load_menus"]);
    webClient.destroy();
    testConfig.actionRegistry.remove("HelloWorldTest");
  });
  QUnit.test("properly load act window actions", async function (assert) {
    assert.expect(7);
    const mockRPC = async function (route, args) {
      assert.step((args && args.method) || route);
    };
    const webClient = await createWebClient({ testConfig, mockRPC });
    webClient.env.bus.trigger("test:hashchange", {
      action: 1,
    });
    await testUtils.nextTick();
    await legacyExtraNextTick();
    assert.containsOnce(webClient, ".o_control_panel");
    assert.containsOnce(webClient, ".o_kanban_view");
    assert.verifySteps([
      "/wowl/load_menus",
      "/web/action/load",
      "load_views",
      "/web/dataset/search_read",
    ]);
    webClient.destroy();
  });
  QUnit.test("properly load records", async function (assert) {
    assert.expect(6);
    const mockRPC = async function (route, args) {
      assert.step((args && args.method) || route);
    };
    const webClient = await createWebClient({ testConfig, mockRPC });
    webClient.env.bus.trigger("test:hashchange", {
      id: 2,
      model: "partner",
    });
    await testUtils.nextTick();
    await legacyExtraNextTick();
    assert.containsOnce(webClient, ".o_form_view");
    assert.strictEqual(
      $(webClient.el).find(".o_control_panel .breadcrumb-item").text(),
      "Second record",
      "should have opened the second record"
    );
    assert.verifySteps(["/wowl/load_menus", "load_views", "read"]);
    webClient.destroy();
  });
  QUnit.test("properly load default record", async function (assert) {
    assert.expect(6);
    const mockRPC = async function (route, args) {
      assert.step((args && args.method) || route);
    };
    const webClient = await createWebClient({ testConfig, mockRPC });
    webClient.env.bus.trigger("test:hashchange", {
      action: 3,
      id: "",
      model: "partner",
      view_type: "form",
    });
    await testUtils.nextTick();
    await legacyExtraNextTick();
    assert.containsOnce(webClient, ".o_form_view");
    assert.verifySteps(["/wowl/load_menus", "/web/action/load", "load_views", "onchange"]);
    webClient.destroy();
  });
  QUnit.test("load requested view for act window actions", async function (assert) {
    assert.expect(7);
    const mockRPC = async function (route, args) {
      assert.step((args && args.method) || route);
    };
    const webClient = await createWebClient({ testConfig, mockRPC });
    webClient.env.bus.trigger("test:hashchange", {
      action: 3,
      view_type: "kanban",
    });
    await testUtils.nextTick();
    await legacyExtraNextTick();
    assert.containsNone(webClient, ".o_list_view");
    assert.containsOnce(webClient, ".o_kanban_view");
    assert.verifySteps([
      "/wowl/load_menus",
      "/web/action/load",
      "load_views",
      "/web/dataset/search_read",
    ]);
    webClient.destroy();
  });
  QUnit.test("lazy load multi record view if mono record one is requested", async function (
    assert
  ) {
    assert.expect(12);
    const mockRPC = async function (route, args) {
      assert.step((args && args.method) || route);
    };
    const webClient = await createWebClient({ testConfig, mockRPC });
    webClient.env.bus.trigger("test:hashchange", {
      action: 3,
      id: 2,
      view_type: "form",
    });
    await testUtils.nextTick();
    await legacyExtraNextTick();
    assert.containsNone(webClient, ".o_list_view");
    assert.containsOnce(webClient, ".o_form_view");
    assert.containsN(webClient, ".o_control_panel .breadcrumb-item", 2);
    assert.strictEqual(
      $(webClient.el).find(".o_control_panel .breadcrumb-item:last").text(),
      "Second record",
      "breadcrumbs should contain the display_name of the opened record"
    );
    // go back to Lst
    await testUtils.dom.click($(webClient.el).find(".o_control_panel .breadcrumb a"));
    await legacyExtraNextTick();
    assert.containsOnce(webClient, ".o_list_view");
    assert.containsNone(webClient, ".o_form_view");
    assert.verifySteps([
      "/wowl/load_menus",
      "/web/action/load",
      "load_views",
      "read",
      "/web/dataset/search_read",
    ]);
    webClient.destroy();
  });
  QUnit.test("lazy load multi record view with previous action", async function (assert) {
    assert.expect(6);
    const webClient = await createWebClient({ testConfig });
    await doAction(webClient, 4);
    assert.containsOnce(
      webClient.el,
      ".o_control_panel .breadcrumb li",
      "there should be one controller in the breadcrumbs"
    );
    assert.strictEqual(
      $(webClient.el).find(".o_control_panel .breadcrumb li").text(),
      "Partners Action 4",
      "breadcrumbs should contain the display_name of the opened record"
    );
    await doAction(webClient, 3, {
      resId: 2,
      viewType: "form",
    });
    assert.containsN(
      webClient.el,
      ".o_control_panel .breadcrumb li",
      3,
      "there should be three controllers in the breadcrumbs"
    );
    assert.strictEqual(
      $(webClient.el).find(".o_control_panel .breadcrumb li").text(),
      "Partners Action 4PartnersSecond record",
      "the breadcrumb elements should be correctly ordered"
    );
    // go back to List
    await testUtils.dom.click($(webClient.el).find(".o_control_panel .breadcrumb a:last"));
    await legacyExtraNextTick();
    assert.containsN(
      webClient.el,
      ".o_control_panel .breadcrumb li",
      2,
      "there should be two controllers in the breadcrumbs"
    );
    assert.strictEqual(
      $(webClient.el).find(".o_control_panel .breadcrumb li").text(),
      "Partners Action 4Partners",
      "the breadcrumb elements should be correctly ordered"
    );
    webClient.destroy();
  });
  QUnit.test("lazy loaded multi record view with failing mono record one", async function (assert) {
    assert.expect(3);
    const mockRPC = async function (route, args) {
      if (args && args.method === "read") {
        return Promise.reject();
      }
    };
    const webClient = await createWebClient({ testConfig, mockRPC });
    await loadState(webClient, {
      action: "3",
      id: "2",
      view_type: "form",
    });
    assert.containsNone(webClient, ".o_form_view");
    assert.containsNone(webClient, ".o_list_view");
    await doAction(webClient, 1);
    assert.containsOnce(webClient, ".o_kanban_view");
    webClient.destroy();
  });
  QUnit.test("change the viewType of the current action", async function (assert) {
    assert.expect(14);
    const mockRPC = async function (route, args) {
      assert.step((args && args.method) || route);
    };
    const webClient = await createWebClient({ testConfig, mockRPC });
    await doAction(webClient, 3);
    assert.containsOnce(webClient, ".o_list_view");
    // switch to kanban view
    webClient.env.bus.trigger("test:hashchange", {
      action: 3,
      view_type: "kanban",
    });
    await testUtils.nextTick();
    await legacyExtraNextTick();
    assert.containsNone(webClient, ".o_list_view");
    assert.containsOnce(webClient, ".o_kanban_view");
    // switch to form view, open record 4
    webClient.env.bus.trigger("test:hashchange", {
      action: 3,
      id: 4,
      view_type: "form",
    });
    await testUtils.nextTick();
    await legacyExtraNextTick();
    assert.containsNone(webClient, ".o_kanban_view");
    assert.containsOnce(webClient, ".o_form_view");
    assert.containsN(
      webClient.el,
      ".o_control_panel .breadcrumb-item",
      2,
      "there should be two controllers in the breadcrumbs"
    );
    assert.strictEqual(
      $(webClient.el).find(".o_control_panel .breadcrumb-item:last").text(),
      "Fourth record",
      "should have opened the requested record"
    );
    // verify steps to ensure that the whole action hasn't been re-executed
    // (if it would have been, /web/action/load and load_views would appear
    // several times)
    assert.verifySteps([
      "/wowl/load_menus",
      "/web/action/load",
      "load_views",
      "/web/dataset/search_read",
      "/web/dataset/search_read",
      "read",
    ]);
    webClient.destroy();
  });
  QUnit.test("change the id of the current action", async function (assert) {
    assert.expect(12);
    const mockRPC = async function (route, args) {
      assert.step((args && args.method) || route);
    };
    const webClient = await createWebClient({ testConfig, mockRPC });
    // execute action 3 and open the first record in a form view
    await doAction(webClient, 3);
    await testUtils.dom.click($(webClient.el).find(".o_list_view .o_data_row:first"));
    await legacyExtraNextTick();
    assert.containsOnce(webClient, ".o_form_view");
    assert.strictEqual(
      $(webClient.el).find(".o_control_panel .breadcrumb-item:last").text(),
      "First record",
      "should have opened the first record"
    );
    // switch to record 4
    webClient.env.bus.trigger("test:hashchange", {
      action: 3,
      id: 4,
      view_type: "form",
    });
    await testUtils.nextTick();
    await legacyExtraNextTick();
    assert.containsOnce(webClient, ".o_form_view");
    assert.containsN(
      webClient.el,
      ".o_control_panel .breadcrumb-item",
      2,
      "there should be two controllers in the breadcrumbs"
    );
    assert.strictEqual(
      $(webClient.el).find(".o_control_panel .breadcrumb-item:last").text(),
      "Fourth record",
      "should have switched to the requested record"
    );
    // verify steps to ensure that the whole action hasn't been re-executed
    // (if it would have been, /web/action/load and load_views would appear
    // twice)
    assert.verifySteps([
      "/wowl/load_menus",
      "/web/action/load",
      "load_views",
      "/web/dataset/search_read",
      "read",
      "read",
    ]);
    webClient.destroy();
  });
  QUnit.test("should push the correct state at the right time", async function (assert) {
    // formerly "should not push a loaded state"
    assert.expect(7);
    testConfig.serviceRegistry.add(
      "router",
      makeFakeRouterService({
        onPushState() {
          assert.step("push_state");
        },
      }),
      true
    );
    const webClient = await createWebClient({ testConfig });
    let currentHash = webClient.env.services.router.current.hash;
    assert.deepEqual(currentHash, {});
    await loadState(webClient, { action: "3" });
    currentHash = webClient.env.services.router.current.hash;
    assert.deepEqual(currentHash, {
      action: "3",
      model: "partner",
      view_type: "list",
    });
    assert.verifySteps(["push_state"], "should have pushed the final state");
    await testUtils.dom.click($(webClient.el).find("tr.o_data_row:first"));
    await legacyExtraNextTick();
    currentHash = webClient.env.services.router.current.hash;
    assert.deepEqual(currentHash, {
      action: "3",
      id: "1",
      model: "partner",
      view_type: "form",
    });
    assert.verifySteps(["push_state"], "should push the state of it changes afterwards");
    webClient.destroy();
  });
  QUnit.test("should not push a loaded state of a legacy client action", async function (assert) {
    assert.expect(6);
    const ClientAction = AbstractAction.extend({
      init: function (parent, action, options) {
        this._super.apply(this, arguments);
        this.controllerID = options.controllerID;
      },
      start: function () {
        const $button = $("<button id='client_action_button'>").text("Click Me!");
        $button.on("click", () => {
          this.trigger_up("push_state", {
            controllerID: this.controllerID,
            state: { someValue: "X" },
          });
        });
        this.$el.append($button);
        return this._super.apply(this, arguments);
      },
    });
    core.action_registry.add("ClientAction", ClientAction);
    testConfig.serviceRegistry.add(
      "router",
      makeFakeRouterService({
        onPushState() {
          assert.step("push_state");
        },
      }),
      true
    );
    const webClient = await createWebClient({ testConfig });
    let currentHash = webClient.env.services.router.current.hash;
    assert.deepEqual(currentHash, {});
    await loadState(webClient, { action: "9" });
    currentHash = webClient.env.services.router.current.hash;
    assert.deepEqual(currentHash, {
      action: "9",
    });
    assert.verifySteps([], "should not push the loaded state");
    await testUtils.dom.click($(webClient.el).find("#client_action_button"));
    await legacyExtraNextTick();
    assert.verifySteps(["push_state"], "should push the state of it changes afterwards");
    currentHash = webClient.env.services.router.current.hash;
    assert.deepEqual(currentHash, {
      action: "9",
      someValue: "X",
    });
    webClient.destroy();
    delete core.action_registry.map.ClientAction;
  });
  QUnit.test("change a param of an ir.actions.client in the url", async function (assert) {
    assert.expect(13);
    const ClientAction = AbstractAction.extend({
      hasControlPanel: true,
      init: function (parent, action) {
        this._super.apply(this, arguments);
        const context = action.context;
        this.a = (context.params && context.params.a) || "default value";
      },
      start: function () {
        assert.step("start");
        this.$(".o_content").text(this.a);
        this.$el.addClass("o_client_action");
        this.trigger_up("push_state", {
          controllerID: this.controllerID,
          state: { a: this.a },
        });
        return this._super.apply(this, arguments);
      },
    });
    core.action_registry.add("ClientAction", ClientAction);
    testConfig.serviceRegistry.add(
      "router",
      makeFakeRouterService({
        onPushState(mode) {
          assert.step(`push_state ${mode}`);
        },
      }),
      true
    );
    const webClient = await createWebClient({ testConfig });
    let currentHash = webClient.env.services.router.current.hash;
    assert.deepEqual(currentHash, {});
    // execute the client action
    await doAction(webClient, 9);
    assert.verifySteps(["start", "push_state push"]);
    currentHash = webClient.env.services.router.current.hash;
    assert.deepEqual(currentHash, {
      action: "9",
      a: "default value",
    });
    assert.strictEqual(
      $(webClient.el).find(".o_client_action .o_content").text(),
      "default value",
      "should have rendered the client action"
    );
    assert.containsN(
      webClient.el,
      ".o_control_panel .breadcrumb-item",
      1,
      "there should be one controller in the breadcrumbs"
    );
    // update param 'a' in the url
    await loadState(webClient, {
      action: "9",
      a: "new value",
    });
    assert.verifySteps(["start", "push_state push"]);
    currentHash = webClient.env.services.router.current.hash;
    assert.deepEqual(currentHash, {
      action: "9",
      a: "new value",
    });
    assert.strictEqual(
      $(webClient.el).find(".o_client_action .o_content").text(),
      "new value",
      "should have rerendered the client action with the correct param"
    );
    assert.containsN(
      webClient.el,
      ".o_control_panel .breadcrumb-item",
      1,
      "there should still be one controller in the breadcrumbs"
    );
    webClient.destroy();
    delete core.action_registry.map.ClientAction;
  });
  QUnit.test("load a window action without id (in a multi-record view)", async function (assert) {
    assert.expect(14);
    const sessionStorage = testConfig.browser.sessionStorage;
    testConfig.browser.sessionStorage = Object.assign(Object.create(sessionStorage), {
      getItem(k) {
        assert.step(`getItem session ${k}`);
        return sessionStorage.getItem(k);
      },
      setItem(k, v) {
        assert.step(`setItem session ${k}`);
        return sessionStorage.setItem(k, v);
      },
    });
    const mockRPC = async (route, args) => {
      assert.step((args && args.method) || route);
    };
    const webClient = await createWebClient({ testConfig, mockRPC });
    await doAction(webClient, 4);
    assert.containsOnce(webClient, ".o_kanban_view", "should display a kanban view");
    assert.strictEqual(
      $(webClient.el).find(".o_control_panel .breadcrumb-item").text(),
      "Partners Action 4",
      "breadcrumbs should display the display_name of the action"
    );
    await loadState(webClient, {
      model: "partner",
      view_type: "list",
    });
    assert.strictEqual(
      $(webClient.el).find(".o_control_panel .breadcrumb-item").text(),
      "Partners Action 4",
      "should still be in the same action"
    );
    assert.containsNone(webClient, ".o_kanban_view", "should no longer display a kanban view");
    assert.containsOnce(webClient, ".o_list_view", "should display a list view");
    assert.verifySteps([
      "/wowl/load_menus",
      "/web/action/load",
      "load_views",
      "/web/dataset/search_read",
      "setItem session current_action",
      "getItem session current_action",
      "/web/dataset/search_read",
      "setItem session current_action",
    ]);
    webClient.destroy();
  });
  QUnit.test("load state supports being given menu_id alone", async function (assert) {
    assert.expect(7);
    testConfig.serverData.menus[666] = {
      id: 666,
      children: [],
      name: "App1",
      appID: 1,
      actionID: 1,
    };
    const mockRPC = async function (route, args) {
      assert.step(route);
    };
    const webClient = await createWebClient({ testConfig, mockRPC });
    await loadState(webClient, {
      menu_id: "666",
    });
    assert.containsOnce(webClient, ".o_kanban_view", "should display a kanban view");
    assert.strictEqual(
      $(webClient.el).find(".o_control_panel .breadcrumb-item").text(),
      "Partners Action 1",
      "breadcrumbs should display the display_name of the action"
    );
    assert.verifySteps([
      "/wowl/load_menus",
      "/web/action/load",
      "/web/dataset/call_kw/partner/load_views",
      "/web/dataset/search_read",
    ]);
    webClient.destroy();
  });
  QUnit.test("load state supports #home", async function (assert) {
    assert.expect(6);
    testConfig.serverData.menus = {
      root: { id: "root", children: [1], name: "root", appID: "root" },
      1: { id: 1, children: [], name: "App1", appID: 1, actionID: 1 },
    };
    const webClient = await createWebClient({ testConfig });
    await testUtils.nextTick(); // wait for the load state (default app)
    await legacyExtraNextTick();
    assert.containsOnce(webClient, ".o_kanban_view"); // action 1 (default app)
    assert.strictEqual(
      $(webClient.el).find(".o_control_panel .breadcrumb-item").text(),
      "Partners Action 1"
    );
    await loadState(webClient, {
      action: "3",
    });
    assert.containsOnce(webClient, ".o_list_view"); // action 3
    assert.strictEqual(
      $(webClient.el).find(".o_control_panel .breadcrumb-item").text(),
      "Partners"
    );
    await loadState(webClient, {
      home: "1",
    });
    assert.containsOnce(webClient, ".o_kanban_view"); // action 1 (default app)
    assert.strictEqual(
      $(webClient.el).find(".o_control_panel .breadcrumb-item").text(),
      "Partners Action 1"
    );
    webClient.destroy();
  });
  QUnit.test("load state supports #home as initial state", async function (assert) {
    assert.expect(7);
    testConfig.serverData.menus = {
      root: { id: "root", children: [1], name: "root", appID: "root" },
      1: { id: 1, children: [], name: "App1", appID: 1, actionID: 1 },
    };
    testConfig.serviceRegistry.add(
      "router",
      makeFakeRouterService({
        initialRoute: {
          hash: { home: "1" },
        },
      }),
      true
    );
    const mockRPC = async function (route, args) {
      assert.step(route);
    };
    const webClient = await createWebClient({ testConfig, mockRPC });
    await testUtils.nextTick(); // wait for the load state (default app)
    await legacyExtraNextTick();
    assert.containsOnce(webClient, ".o_kanban_view", "should display a kanban view");
    assert.strictEqual(
      $(webClient.el).find(".o_control_panel .breadcrumb-item").text(),
      "Partners Action 1"
    );
    assert.verifySteps([
      "/wowl/load_menus",
      "/web/action/load",
      "/web/dataset/call_kw/partner/load_views",
      "/web/dataset/search_read",
    ]);
    webClient.destroy();
  });
  QUnit.test("load state: in a form view, remove the id from the state", async function (assert) {
    assert.expect(13);
    testConfig.serverData.actions[999] = {
      id: 999,
      name: "Partner",
      res_model: "partner",
      type: "ir.actions.act_window",
      views: [
        [false, "list"],
        [666, "form"],
      ],
    };
    const mockRPC = async (route, args) => {
      assert.step(route);
    };
    const webClient = await createWebClient({ testConfig, mockRPC });
    await doAction(webClient, 999, { viewType: "form", resId: 2 });
    assert.containsOnce(webClient, ".o_form_view");
    assert.containsN(webClient, ".breadcrumb-item", 2);
    assert.strictEqual(
      $(webClient.el).find(".o_control_panel .breadcrumb-item.active").text(),
      "Second record"
    );
    assert.verifySteps([
      "/wowl/load_menus",
      "/web/action/load",
      "/web/dataset/call_kw/partner/load_views",
      "/web/dataset/call_kw/partner/read",
    ]);
    await loadState(webClient, { action: "999", view_type: "form", id: undefined });
    assert.verifySteps(["/web/dataset/call_kw/partner/onchange"]);
    assert.containsOnce(webClient, ".o_form_view.o_form_editable");
    assert.containsN(webClient, ".breadcrumb-item", 2);
    assert.strictEqual(
      $(webClient.el).find(".o_control_panel .breadcrumb-item.active").text(),
      "New"
    );
    webClient.destroy();
  });
  QUnit.test("hashchange does not trigger canberemoved right away", async function (assert) {
    assert.expect(9);
    const ClientAction = AbstractAction.extend({
      start() {
        this.$el.text("Hello World");
        this.$el.addClass("o_client_action_test");
      },
      canBeRemoved() {
        assert.step("canBeRemoved");
        return this._super.apply(this, arguments);
      },
    });
    core.action_registry.add("ClientAction", ClientAction);
    const ClientAction2 = AbstractAction.extend({
      start() {
        this.$el.text("Hello World");
        this.$el.addClass("o_client_action_test_2");
      },
      canBeRemoved() {
        assert.step("canBeRemoved_2");
        return this._super.apply(this, arguments);
      },
    });
    core.action_registry.add("ClientAction2", ClientAction2);
    testConfig.serviceRegistry.add(
      "router",
      makeFakeRouterService({ onPushState: () => assert.step("hashSet") }),
      true
    );
    const webClient = await createWebClient({ testConfig });
    assert.verifySteps([]);
    await doAction(webClient, 9);
    assert.verifySteps(["hashSet"]);
    assert.containsOnce(webClient.el, ".o_client_action_test");
    assert.verifySteps([]);
    await doAction(webClient, "ClientAction2");
    assert.containsOnce(webClient.el, ".o_client_action_test_2");
    assert.verifySteps(["canBeRemoved", "hashSet"]);
    webClient.destroy();
    delete core.action_registry.map.ClientAction;
    delete core.action_registry.map.ClientAction2;
  });
});
