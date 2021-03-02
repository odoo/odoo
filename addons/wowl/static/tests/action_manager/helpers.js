/** @odoo-module **/
import { WebClient } from "../../src/webclient/webclient";
import { Registry } from "../../src/core/registry";
import { makeFakeUserService, nextTick } from "../helpers/index";
import { legacyExtraNextTick, makeTestEnv, mount } from "../helpers/utility";
import { notificationService } from "../../src/notifications/notification_service";
import { dialogService } from "../../src/services/dialog_service";
import { menuService } from "../../src/services/menu_service";
import { actionService } from "../../src/actions/action_service";
import { makeFakeRouterService, fakeTitleService, makeFakeDeviceService } from "../helpers/mocks";
import { viewService } from "../../src/views/view_service";
import { modelService } from "../../src/services/model_service";
import { makeRAMLocalStorage } from "../../src/env";
import { makeLegacyActionManagerService, mapLegacyEnvToWowlEnv } from "../../src/legacy/utils";
import { getLegacy } from "wowl.test_legacy";
import { actionRegistry } from "../../src/actions/action_registry";
import { viewRegistry } from "../../src/views/view_registry";
import { uiService } from "../../src/services/ui/ui";
import { effectService } from "../../src/effects/effect_service";

const { Component, tags } = owl;

// -----------------------------------------------------------------------------
// Utils
// -----------------------------------------------------------------------------
export async function createWebClient(params) {
  const { AbstractAction, AbstractController, testUtils } = getLegacy();
  const { patch, unpatch } = testUtils.mock;
  // With the compatibility layer, the action manager keeps legacy alive if they
  // are still acessible from the breacrumbs. They are manually destroyed as soon
  // as they are no longer referenced in the stack. This works fine in production,
  // because the webclient is never destroyed. However, at the end of each test,
  // we destroy the webclient and expect every legacy that has been instantiated
  // to be destroyed. We thus need to manually destroy them here.
  const controllers = [];
  patch(AbstractAction, {
    init() {
      this._super(...arguments);
      controllers.push(this);
    },
  });
  patch(AbstractController, {
    init() {
      this._super(...arguments);
      controllers.push(this);
    },
  });
  const mockRPC = params.mockRPC || undefined;
  const env = await makeTestEnv({
    ...params.testConfig,
    mockRPC,
  });
  const wc = await mount(WebClient, { env });
  const _destroy = wc.destroy;
  wc.destroy = () => {
    _destroy.call(wc);
    for (const controller of controllers) {
      if (!controller.isDestroyed()) {
        controller.destroy();
      }
    }
    unpatch(AbstractAction);
    unpatch(AbstractController);
  };
  wc._____testname = QUnit.config.current.testName;
  addLegacyMockEnvironment(wc, params.testConfig, params.legacyParams);
  await legacyExtraNextTick();
  return wc;
}
/**
 * Remove this as soon as we drop the legacy support
 */
function addLegacyMockEnvironment(comp, testConfig, legacyParams = {}) {
  const cleanUps = [];
  const legacy = getLegacy();
  // setup a legacy env
  const dataManager = Object.assign(
    {
      load_action: (actionID, context) => {
        return comp.env.services.rpc("/web/action/load", {
          action_id: actionID,
          additional_context: context,
        });
      },
      load_views: async (params, options) => {
        const result = await comp.env.services.rpc(`/web/dataset/call_kw/${params.model}`, {
          args: [],
          kwargs: {
            context: params.context,
            options: options,
            views: params.views_descr,
          },
          method: "load_views",
          model: params.model,
        });
        const views = result.fields_views;
        for (const [_, viewType] of params.views_descr) {
          const fvg = views[viewType];
          fvg.viewFields = fvg.fields;
          fvg.fields = result.fields;
        }
        if (params.favoriteFilters && "search" in views) {
          views.search.favoriteFilters = params.favoriteFilters;
        }
        return views;
      },
      load_filters: (params) => {
        if (QUnit.config.debug) {
          console.log("[mock] load_filters", params);
        }
        return Promise.resolve([]);
      },
    },
    legacyParams.dataManager
  );
  const legacyEnv = legacy.makeTestEnvironment({ dataManager, bus: legacy.core.bus });
  Component.env = legacyEnv;
  mapLegacyEnvToWowlEnv(legacyEnv, comp.env);
  // deploy the legacyActionManagerService (in Wowl env)
  const legacyActionManagerService = makeLegacyActionManagerService(legacyEnv);
  testConfig.serviceRegistry.add("legacy_action_manager", legacyActionManagerService);
  // patch DebouncedField delay
  const debouncedField = legacy.basicFields.DebouncedField;
  const initialDebouncedVal = debouncedField.prototype.DEBOUNCE;
  debouncedField.prototype.DEBOUNCE = 0;
  cleanUps.push(() => (debouncedField.prototype.DEBOUNCE = initialDebouncedVal));
  // clean up at end of test
  const compDestroy = comp.destroy.bind(comp);
  comp.destroy = () => {
    cleanUps.forEach((fn) => fn());
    compDestroy();
  };
}
export async function doAction(env, ...args) {
  if (env instanceof Component) {
    env = env.env;
  }
  try {
    await env.services.action.doAction(...args);
  } finally {
    await legacyExtraNextTick();
  }
}
export async function loadState(env, state) {
  if (env instanceof Component) {
    env = env.env;
  }
  env.bus.trigger("test:hashchange", state);
  await nextTick();
  await legacyExtraNextTick();
}
export function getActionManagerTestConfig() {
  const browser = {
    setTimeout: window.setTimeout.bind(window),
    clearTimeout: window.clearTimeout.bind(window),
    localStorage: makeRAMLocalStorage(),
    sessionStorage: makeRAMLocalStorage(),
  };
  // build the service registry
  const serviceRegistry = new Registry();
  serviceRegistry
    .add("user", makeFakeUserService())
    .add(notificationService.name, notificationService)
    .add(dialogService.name, dialogService)
    .add("menu", menuService)
    .add("action", actionService)
    .add("router", makeFakeRouterService())
    .add("view_manager", viewService)
    .add("model", modelService)
    .add(fakeTitleService.name, fakeTitleService)
    .add(uiService.name, uiService)
    .add("device", makeFakeDeviceService())
    .add(effectService.name, effectService);
  // build the action registry: copy the real action registry, and add an
  // additional basic client action
  const testActionRegistry = new Registry();
  for (const [key, action] of actionRegistry.getEntries()) {
    testActionRegistry.add(key, action);
  }
  class TestClientAction extends Component {}
  TestClientAction.template = tags.xml`
      <div class="test_client_action">
        ClientAction_<t t-esc="props.action.params?.description"/>
      </div>`;
  testActionRegistry.add("__test__client__action__", TestClientAction);
  // build a copy of the view registry
  const testViewRegistry = new Registry();
  for (const [key, view] of viewRegistry.getEntries()) {
    testViewRegistry.add(key, view);
  }
  // build the mocked server data
  const menus = {
    root: { id: "root", children: [0, 1, 2], name: "root", appID: "root" },
    // id:0 is a hack to not load anything at webClient mount
    0: { id: 0, children: [], name: "UglyHack", appID: 0 },
    1: { id: 1, children: [], name: "App1", appID: 1, actionID: 1001 },
    2: { id: 2, children: [], name: "App2", appID: 2, actionID: 1002 },
  };
  const actionsArray = [
    {
      id: 1,
      name: "Partners Action 1",
      res_model: "partner",
      type: "ir.actions.act_window",
      views: [[1, "kanban"]],
    },
    {
      id: 2,
      type: "ir.actions.server",
    },
    {
      id: 3,
      name: "Partners",
      res_model: "partner",
      type: "ir.actions.act_window",
      views: [
        [false, "list"],
        [1, "kanban"],
        [false, "form"],
      ],
    },
    {
      id: 4,
      name: "Partners Action 4",
      res_model: "partner",
      type: "ir.actions.act_window",
      views: [
        [1, "kanban"],
        [2, "list"],
        [false, "form"],
      ],
    },
    {
      id: 5,
      name: "Create a Partner",
      res_model: "partner",
      target: "new",
      type: "ir.actions.act_window",
      views: [[false, "form"]],
    },
    {
      id: 6,
      name: "Partner",
      res_id: 2,
      res_model: "partner",
      target: "inline",
      type: "ir.actions.act_window",
      views: [[false, "form"]],
    },
    {
      id: 7,
      name: "Some Report",
      report_name: "some_report",
      report_type: "qweb-pdf",
      type: "ir.actions.report",
    },
    {
      id: 8,
      name: "Favorite Ponies",
      res_model: "pony",
      type: "ir.actions.act_window",
      views: [
        [false, "list"],
        [false, "form"],
      ],
    },
    {
      id: 9,
      name: "A Client Action",
      tag: "ClientAction",
      type: "ir.actions.client",
    },
    {
      id: 10,
      type: "ir.actions.act_window_close",
    },
    {
      id: 11,
      name: "Another Report",
      report_name: "another_report",
      report_type: "qweb-pdf",
      type: "ir.actions.report",
      close_on_report_download: true,
    },
    {
      id: 12,
      name: "Some HTML Report",
      report_name: "some_report",
      report_type: "qweb-html",
      type: "ir.actions.report",
    },
    {
      id: 24,
      name: "Partner",
      res_id: 2,
      res_model: "partner",
      type: "ir.actions.act_window",
      views: [[666, "form"]],
    },
    {
      id: 25,
      name: "Create a Partner",
      res_model: "partner",
      target: "new",
      type: "ir.actions.act_window",
      views: [[1, "form"]],
    },
    {
      id: 1001,
      tag: "__test__client__action__",
      target: "main",
      type: "ir.actions.client",
      params: { description: "Id 1" },
    },
    {
      id: 1002,
      tag: "__test__client__action__",
      target: "main",
      type: "ir.actions.client",
      params: { description: "Id 2" },
    },
    {
      xmlId: "wowl.client_action",
      id: 1099,
      tag: "__test__client__action__",
      target: "main",
      type: "ir.actions.client",
      params: { description: "xmlId" },
    },
  ];
  const actions = {};
  actionsArray.forEach((act) => {
    actions[act.xmlId || act.id] = act;
  });
  const archs = {
    // kanban views
    "partner,1,kanban":
      '<kanban><templates><t t-name="kanban-box">' +
      '<div class="oe_kanban_global_click"><field name="foo"/></div>' +
      "</t></templates></kanban>",
    // list views
    "partner,false,list": '<tree><field name="foo"/></tree>',
    "partner,2,list": '<tree limit="3"><field name="foo"/></tree>',
    "pony,false,list": '<tree><field name="name"/></tree>',
    // form views
    "partner,false,form":
      "<form>" +
      "<header>" +
      '<button name="object" string="Call method" type="object"/>' +
      '<button name="4" string="Execute action" type="action"/>' +
      "</header>" +
      "<group>" +
      '<field name="display_name"/>' +
      '<field name="foo"/>' +
      "</group>" +
      "</form>",
    "partner,1,form": `
      <form>
      <footer>
      <button class="btn-primary" string="Save" special="save"/>
      </footer>
      </form>`,
    "partner,666,form": `<form>
      <header></header>
      <sheet>
      <div class="oe_button_box" name="button_box" modifiers="{}">
      <button class="oe_stat_button" type="action" name="1" icon="fa-star" context="{'default_partner': active_id}">
      <field string="Partners" name="o2m" widget="statinfo"/>
      </button>
      </div>
      <field name="display_name"/>
      </sheet>
      </form>`,
    "pony,false,form": "<form>" + '<field name="name"/>' + "</form>",
    // search views
    "partner,false,search": '<search><field name="foo" string="Foo"/></search>',
    "partner,1,search":
      "<search>" + '<filter name="bar" help="Bar" domain="[(\'bar\', \'=\', 1)]"/>' + "</search>",
    "pony,false,search": "<search></search>",
  };
  const models = {
    partner: {
      fields: {
        id: { string: "Id", type: "integer" },
        foo: { string: "Foo", type: "char" },
        bar: { string: "Bar", type: "many2one", relation: "partner" },
        o2m: { string: "One2Many", type: "one2many", relation: "partner", relation_field: "bar" },
        m2o: { string: "Many2one", type: "many2one", relation: "partner" },
      },
      records: [
        { id: 1, display_name: "First record", foo: "yop", bar: 2, o2m: [2, 3], m2o: 3 },
        { id: 2, display_name: "Second record", foo: "blip", bar: 1, o2m: [1, 4, 5], m2o: 3 },
        { id: 3, display_name: "Third record", foo: "gnap", bar: 1, o2m: [], m2o: 1 },
        { id: 4, display_name: "Fourth record", foo: "plop", bar: 2, o2m: [], m2o: 1 },
        { id: 5, display_name: "Fifth record", foo: "zoup", bar: 2, o2m: [], m2o: 1 },
      ],
    },
    pony: {
      fields: {
        id: { string: "Id", type: "integer" },
        name: { string: "Name", type: "char" },
      },
      records: [
        { id: 4, name: "Twilight Sparkle" },
        { id: 6, name: "Applejack" },
        { id: 9, name: "Fluttershy" },
      ],
    },
  };
  const serverData = {
    models,
    views: archs,
    actions,
    menus,
  };
  return {
    actionRegistry: testActionRegistry,
    browser,
    serverData,
    serviceRegistry,
    viewRegistry: testViewRegistry,
  };
}
