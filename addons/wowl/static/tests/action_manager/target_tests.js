/** @odoo-module **/
import { legacyExtraNextTick } from "../helpers/utility";
import { getLegacy } from "wowl.test_legacy";
import { actionRegistry } from "../../src/actions/action_registry";
import { viewRegistry } from "../../src/views/view_registry";
import { createWebClient, doAction, getActionManagerTestConfig } from "./helpers";
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
  QUnit.module('Actions in target="new"');
  QUnit.test('can execute act_window actions in target="new"', async function (assert) {
    assert.expect(8);
    const mockRPC = async (route, args) => {
      assert.step((args && args.method) || route);
    };
    const webClient = await createWebClient({ testConfig, mockRPC });
    await doAction(webClient, 5);
    assert.containsOnce(
      document.body,
      ".o_technical_modal .o_form_view",
      "should have rendered a form view in a modal"
    );
    assert.hasClass(
      $(".o_technical_modal .modal-body")[0],
      "o_act_window",
      "dialog main element should have classname 'o_act_window'"
    );
    assert.hasClass(
      $(".o_technical_modal .o_form_view")[0],
      "o_form_editable",
      "form view should be in edit mode"
    );
    assert.verifySteps(["/wowl/load_menus", "/web/action/load", "load_views", "onchange"]);
    webClient.destroy();
  });
  QUnit.test("chained action on_close", async function (assert) {
    assert.expect(4);
    function onClose(closeInfo) {
      assert.strictEqual(closeInfo, "smallCandle");
      assert.step("Close Action");
    }
    const webClient = await createWebClient({ testConfig });
    await doAction(webClient, 5, { onClose });
    // a target=new action shouldn't activate the on_close
    await doAction(webClient, 5);
    assert.verifySteps([]);
    // An act_window_close should trigger the on_close
    await doAction(webClient, { type: "ir.actions.act_window_close", infos: "smallCandle" });
    assert.verifySteps(["Close Action"]);
    webClient.destroy();
  });
  QUnit.test("footer buttons are moved to the dialog footer", async function (assert) {
    assert.expect(3);
    testConfig.serverData.views["partner,false,form"] = `
      <form>
        <field name="display_name"/>
        <footer>
          <button string="Create" type="object" class="infooter"/>
        </footer>
      </form>`;
    const webClient = await createWebClient({ testConfig });
    await doAction(webClient, 5);
    assert.containsNone(
      $(".o_technical_modal .modal-body")[0],
      "button.infooter",
      "the button should not be in the body"
    );
    assert.containsOnce(
      $(".o_technical_modal .modal-footer")[0],
      "button.infooter",
      "the button should be in the footer"
    );
    assert.containsOnce(
      $(".o_technical_modal .modal-footer")[0],
      "button",
      "the modal footer should only contain one button"
    );
    webClient.destroy();
  });
  QUnit.test("Button with `close` attribute closes dialog", async function (assert) {
    assert.expect(19);
    testConfig.serverData.views = {
      "partner,false,form": `
        <form>
          <header>
            <button string="Open dialog" name="5" type="action"/>
          </header>
        </form>
      `,
      "partner,view_ref,form": `
          <form>
            <footer>
              <button string="I close the dialog" name="some_method" type="object" close="1"/>
            </footer>
          </form>
      `,
      "partner,false,search": "<search></search>",
    };
    testConfig.serverData.actions[4] = {
      id: 4,
      name: "Partners Action 4",
      res_model: "partner",
      type: "ir.actions.act_window",
      views: [[false, "form"]],
    };
    testConfig.serverData.actions[5] = {
      id: 5,
      name: "Create a Partner",
      res_model: "partner",
      target: "new",
      type: "ir.actions.act_window",
      views: [["view_ref", "form"]],
    };
    const mockRPC = async (route, args) => {
      assert.step(route);
      if (route === "/web/dataset/call_button" && args.method === "some_method") {
        return {
          tag: "display_notification",
          type: "ir.actions.client",
        };
      }
    };
    const webClient = await createWebClient({ testConfig, mockRPC });
    assert.verifySteps(["/wowl/load_menus"]);
    await doAction(webClient, 4);
    assert.verifySteps([
      "/web/action/load",
      "/web/dataset/call_kw/partner/load_views",
      "/web/dataset/call_kw/partner/onchange",
    ]);
    await testUtils.dom.click(`button[name="5"]`);
    assert.verifySteps([
      "/web/dataset/call_kw/partner/create",
      "/web/dataset/call_kw/partner/read",
      "/web/action/load",
      "/web/dataset/call_kw/partner/load_views",
      "/web/dataset/call_kw/partner/onchange",
    ]);
    await legacyExtraNextTick();
    assert.strictEqual($(".modal").length, 1, "It should display a modal");
    await testUtils.dom.click(`button[name="some_method"]`);
    assert.verifySteps([
      "/web/dataset/call_kw/partner/create",
      "/web/dataset/call_kw/partner/read",
      "/web/dataset/call_button",
      "/web/dataset/call_kw/partner/read",
    ]);
    await legacyExtraNextTick();
    assert.strictEqual($(".modal").length, 0, "It should have closed the modal");
    webClient.destroy();
  });
  QUnit.test('on_attach_callback is called for actions in target="new"', async function (assert) {
    assert.expect(3);
    const ClientAction = AbstractAction.extend({
      on_attach_callback: function () {
        assert.step("on_attach_callback");
        assert.containsOnce(
          document.body,
          ".modal .o_test",
          "should have rendered the client action in a dialog"
        );
      },
      start: function () {
        this.$el.addClass("o_test");
      },
    });
    core.action_registry.add("test", ClientAction);
    const webClient = await createWebClient({ testConfig });
    await doAction(webClient, {
      tag: "test",
      target: "new",
      type: "ir.actions.client",
    });
    assert.verifySteps(["on_attach_callback"]);
    webClient.destroy();
    delete core.action_registry.map.test;
  });
  QUnit.test(
    'footer buttons are updated when having another action in target "new"',
    async function (assert) {
      assert.expect(9);
      testConfig.serverData.views["partner,false,form"] =
        "<form>" +
        '<field name="display_name"/>' +
        "<footer>" +
        '<button string="Create" type="object" class="infooter"/>' +
        "</footer>" +
        "</form>";
      const webClient = await createWebClient({ testConfig });
      await doAction(webClient, 5);
      assert.containsNone(webClient.el, '.o_technical_modal .modal-body button[special="save"]');
      assert.containsNone(webClient.el, ".o_technical_modal .modal-body button.infooter");
      assert.containsOnce(webClient.el, ".o_technical_modal .modal-footer button.infooter");
      assert.containsOnce(webClient.el, ".o_technical_modal .modal-footer button");
      await doAction(webClient, 25);
      assert.containsNone(webClient.el, ".o_technical_modal .modal-body button.infooter");
      assert.containsNone(webClient.el, ".o_technical_modal .modal-footer button.infooter");
      assert.containsNone(webClient.el, '.o_technical_modal .modal-body button[special="save"]');
      assert.containsOnce(webClient.el, '.o_technical_modal .modal-footer button[special="save"]');
      assert.containsOnce(webClient.el, ".o_technical_modal .modal-footer button");
      webClient.destroy();
    }
  );
  QUnit.test(
    'buttons of client action in target="new" and transition to MVC action',
    async function (assert) {
      assert.expect(4);
      const ClientAction = AbstractAction.extend({
        renderButtons($target) {
          const button = document.createElement("button");
          button.setAttribute("class", "o_stagger_lee");
          $target[0].appendChild(button);
        },
      });
      core.action_registry.add("test", ClientAction);
      const webClient = await createWebClient({ testConfig });
      await doAction(webClient, {
        tag: "test",
        target: "new",
        type: "ir.actions.client",
      });
      assert.containsOnce(webClient.el, ".modal footer button.o_stagger_lee");
      assert.containsNone(webClient.el, '.modal footer button[special="save"]');
      await doAction(webClient, 25);
      assert.containsNone(webClient.el, ".modal footer button.o_stagger_lee");
      assert.containsOnce(webClient.el, '.modal footer button[special="save"]');
      webClient.destroy();
      delete core.action_registry.map.test;
    }
  );
  QUnit.module('Actions in target="inline"');
  QUnit.test(
    'form views for actions in target="inline" open in edit mode',
    async function (assert) {
      assert.expect(6);
      const mockRPC = async (route, args) => {
        assert.step(args.method || route);
      };
      const webClient = await createWebClient({ testConfig, mockRPC });
      await doAction(webClient, 6);
      assert.containsOnce(
        webClient,
        ".o_form_view.o_form_editable",
        "should have rendered a form view in edit mode"
      );
      assert.verifySteps(["/wowl/load_menus", "/web/action/load", "load_views", "read"]);
      webClient.destroy();
    }
  );
  QUnit.test("breadcrumbs and actions with target inline", async function (assert) {
    assert.expect(4);
    testConfig.serverData.actions[4].views = [[false, "form"]];
    testConfig.serverData.actions[4].target = "inline";
    const webClient = await createWebClient({ testConfig });
    await doAction(webClient, 4);
    assert.containsNone(webClient, ".o_control_panel");
    await doAction(webClient, 1, { clearBreadcrumbs: true });
    assert.containsOnce(webClient, ".o_control_panel");
    assert.isVisible(webClient.el.querySelector(".o_control_panel"));
    assert.strictEqual(
      webClient.el.querySelector(".o_control_panel .breadcrumb").textContent,
      "Partners Action 1",
      "should have only one current action visible in breadcrumbs"
    );
    webClient.destroy();
  });
  QUnit.module('Actions in target="fullscreen"');
  QUnit.test(
    'correctly execute act_window actions in target="fullscreen"',
    async function (assert) {
      assert.expect(3);
      testConfig.serverData.actions[1].target = "fullscreen";
      const webClient = await createWebClient({ testConfig });
      await doAction(webClient, 1);
      assert.containsOnce(webClient.el, ".o_control_panel", "should have rendered a control panel");
      assert.containsOnce(webClient, ".o_kanban_view", "should have rendered a kanban view");
      assert.isNotVisible(webClient.el.querySelector(".o_main_navbar"));
      webClient.destroy();
    }
  );
  QUnit.test('fullscreen on action change: back to a "current" action', async function (assert) {
    assert.expect(3);
    testConfig.serverData.actions[1].target = "fullscreen";
    testConfig.serverData.views[
      "partner,false,form"
    ] = `<form><button name="1" type="action" class="oe_stat_button" /></form>`;
    const webClient = await createWebClient({ testConfig });
    await doAction(webClient, 6);
    assert.isVisible(webClient.el.querySelector(".o_main_navbar"));
    await testUtils.dom.click($(webClient.el).find("button[name=1]"));
    await legacyExtraNextTick();
    assert.isNotVisible(webClient.el.querySelector(".o_main_navbar"));
    await testUtils.dom.click($(webClient.el).find(".breadcrumb li a:first"));
    await legacyExtraNextTick();
    assert.isVisible(webClient.el.querySelector(".o_main_navbar"));
    webClient.destroy();
  });
  QUnit.test('fullscreen on action change: all "fullscreen" actions', async function (assert) {
    assert.expect(3);
    testConfig.serverData.actions[6].target = "fullscreen";
    testConfig.serverData.views[
      "partner,false,form"
    ] = `<form><button name="1" type="action" class="oe_stat_button" /></form>`;
    const webClient = await createWebClient({ testConfig });
    await doAction(webClient, 6);
    assert.isNotVisible(webClient.el.querySelector(".o_main_navbar"));
    await testUtils.dom.click($(webClient.el).find("button[name=1]"));
    await legacyExtraNextTick();
    assert.isNotVisible(webClient.el.querySelector(".o_main_navbar"));
    await testUtils.dom.click($(webClient.el).find(".breadcrumb li a:first"));
    await legacyExtraNextTick();
    assert.isNotVisible(webClient.el.querySelector(".o_main_navbar"));
    webClient.destroy();
  });
  QUnit.test(
    'fullscreen on action change: back to another "current" action',
    async function (assert) {
      assert.expect(8);
      testConfig.serverData.menus = {
        root: { id: "root", children: [1], name: "root", appID: "root" },
        1: { id: 1, children: [], name: "MAIN APP", appID: 1, actionID: 6 },
      };
      testConfig.serverData.actions[1].target = "fullscreen";
      testConfig.serverData.views["partner,false,form"] =
        '<form><button name="24" type="action" class="oe_stat_button"/></form>';
      const webClient = await createWebClient({ testConfig });
      await testUtils.nextTick(); // wait for the load state (default app)
      await legacyExtraNextTick();
      assert.containsOnce(webClient, "nav .o_menu_brand");
      assert.strictEqual($(webClient.el).find("nav .o_menu_brand").text(), "MAIN APP");
      assert.doesNotHaveClass(webClient.el, "o_fullscreen");
      await testUtils.dom.click($(webClient.el).find('button[name="24"]'));
      await legacyExtraNextTick();
      assert.doesNotHaveClass(webClient.el, "o_fullscreen");
      await testUtils.dom.click($(webClient.el).find('button[name="1"]'));
      await legacyExtraNextTick();
      assert.hasClass(webClient.el, "o_fullscreen");
      await testUtils.dom.click($(webClient.el).find(".breadcrumb li a")[1]);
      await legacyExtraNextTick();
      assert.doesNotHaveClass(webClient.el, "o_fullscreen");
      assert.containsOnce(webClient, "nav .o_menu_brand");
      assert.strictEqual($(webClient.el).find("nav .o_menu_brand").text(), "MAIN APP");
      webClient.destroy();
    }
  );
});
