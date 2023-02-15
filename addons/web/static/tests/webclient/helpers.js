/** @odoo-module **/

import { dialogService } from "@web/core/dialog/dialog_service";
import { notificationService } from "@web/core/notifications/notification_service";
import { ormService } from "@web/core/orm_service";
import { popoverService } from "@web/core/popover/popover_service";
import { registry } from "@web/core/registry";
import { legacyServiceProvider } from "@web/legacy/legacy_service_provider";
import {
    makeLegacyNotificationService,
    mapLegacyEnvToWowlEnv,
    makeLegacySessionService,
} from "@web/legacy/utils";
import { makeLegacyActionManagerService } from "@web/legacy/backend_utils";
import { generateLegacyLoadViewsResult } from "@web/legacy/legacy_load_views";
import { viewService } from "@web/views/view_service";
import { actionService } from "@web/webclient/actions/action_service";
import { effectService } from "@web/core/effects/effect_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { menuService } from "@web/webclient/menus/menu_service";
import { WebClient } from "@web/webclient/webclient";
// This import is needed because of it's sideeffects, for exemple :
// web.test_utils easyload xml templates at line : 124:130.
// Also it set the autocomplete delay time for the field Many2One at 0 for the tests at line : 132:137
import "web.test_legacy";
import AbstractService from "web.AbstractService";
import ActionMenus from "web.ActionMenus";
import basicFields from "web.basic_fields";
import Registry from "web.Registry";
import core from "web.core";
import makeTestEnvironment from "web.test_env";
import { registerCleanup } from "../helpers/cleanup";
import { makeTestEnv } from "../helpers/mock_env";
import {
    fakeTitleService,
    fakeCompanyService,
    makeFakeLocalizationService,
    makeFakeRouterService,
    makeFakeHTTPService,
    makeFakeUserService,
} from "../helpers/mock_services";
import {
    getFixture,
    legacyExtraNextTick,
    mount,
    nextTick,
    patchWithCleanup,
} from "../helpers/utils";
import session from "web.session";
import LegacyMockServer from "web.MockServer";
import Widget from "web.Widget";
import { uiService } from "@web/core/ui/ui_service";
import { ClientActionAdapter, ViewAdapter } from "@web/legacy/action_adapters";
import { commandService } from "@web/core/commands/command_service";
import { ConnectionAbortedError } from "@web/core/network/rpc_service";
import { CustomFavoriteItem } from "@web/search/favorite_menu/custom_favorite_item";
import { standaloneAdapter } from "web.OwlCompatibility";

import { Component, onMounted, xml } from "@odoo/owl";

const actionRegistry = registry.category("actions");
const serviceRegistry = registry.category("services");
const favoriteMenuRegistry = registry.category("favoriteMenu");

/**
 * Builds the required registries for tests using a WebClient.
 * We use a default version of each required registry item.
 * If the registry already contains one of those items,
 * the existing one is kept (it means it has been added in the test
 * directly, e.g. to have a custom version of the item).
 */
export function setupWebClientRegistries() {
    const favoriveMenuItems = {
        "custom-favorite-item": {
            value: { Component: CustomFavoriteItem, groupNumber: 3 },
            options: { sequence: 0 },
        },
    };
    for (const [key, { value, options }] of Object.entries(favoriveMenuItems)) {
        if (!favoriteMenuRegistry.contains(key)) {
            favoriteMenuRegistry.add(key, value, options);
        }
    }
    const services = {
        action: () => actionService,
        command: () => commandService,
        dialog: () => dialogService,
        effect: () => effectService,
        hotkey: () => hotkeyService,
        http: () => makeFakeHTTPService(),
        legacy_service_provider: () => legacyServiceProvider,
        localization: () => makeFakeLocalizationService(),
        menu: () => menuService,
        notification: () => notificationService,
        orm: () => ormService,
        popover: () => popoverService,
        router: () => makeFakeRouterService(),
        title: () => fakeTitleService,
        ui: () => uiService,
        user: () => makeFakeUserService(),
        view: () => viewService,
        company: () => fakeCompanyService,
    };
    for (const serviceName in services) {
        if (!serviceRegistry.contains(serviceName)) {
            serviceRegistry.add(serviceName, services[serviceName]());
        }
    }
}

/**
 * Remove this as soon as we drop the legacy support
 */
export async function addLegacyMockEnvironment(env, legacyParams = {}) {
    // setup a legacy env
    const dataManager = Object.assign(
        {
            load_action: (actionID, context) => {
                return env.services.rpc("/web/action/load", {
                    action_id: actionID,
                    additional_context: context,
                });
            },
            load_views: async (params, options) => {
                let result = await env.services.rpc(`/web/dataset/call_kw/${params.model}`, {
                    args: [],
                    kwargs: {
                        context: params.context,
                        options: options,
                        views: params.views_descr,
                    },
                    method: "get_views",
                    model: params.model,
                });
                const { models, views: _views } = result;
                result = generateLegacyLoadViewsResult(params.model, _views, models);
                const views = result.fields_views;
                for (const [, viewType] of params.views_descr) {
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

    // clear the ActionMenus registry to prevent external code from doing unknown rpcs
    const actionMenusRegistry = ActionMenus.registry;
    ActionMenus.registry = new Registry();
    registerCleanup(() => (ActionMenus.registry = actionMenusRegistry));

    let localSession;
    if (legacyParams && legacyParams.getTZOffset) {
        patchWithCleanup(session, {
            getTZOffset: legacyParams.getTZOffset,
        });
        localSession = { getTZOffset: legacyParams.getTZOffset };
    }

    const baseEnv = { dataManager, bus: core.bus, session: localSession };
    const legacyEnv = makeTestEnvironment(Object.assign(baseEnv, legacyParams.env));

    if (legacyParams.serviceRegistry) {
        const legacyServiceMap = core.serviceRegistry.map;
        core.serviceRegistry.map = legacyParams.serviceRegistry.map;
        // notification isn't a deployed service, but it is added by `makeTestEnvironment`.
        // Here, we want full control on the deployed services, so we simply remove it.
        delete legacyEnv.services.notification;
        AbstractService.prototype.deployServices(legacyEnv);
        registerCleanup(() => {
            core.serviceRegistry.map = legacyServiceMap;
        });
    }

    Component.env = legacyEnv;
    mapLegacyEnvToWowlEnv(legacyEnv, env);
    function patchLegacySession() {
        const userContext = Object.getOwnPropertyDescriptor(session, "user_context");
        registerCleanup(() => {
            Object.defineProperty(session, "user_context", userContext);
        });
    }
    patchLegacySession();
    serviceRegistry.add("legacy_session", makeLegacySessionService(legacyEnv, session));
    // deploy the legacyActionManagerService (in Wowl env)
    const legacyActionManagerService = makeLegacyActionManagerService(legacyEnv);
    serviceRegistry.add("legacy_action_manager", legacyActionManagerService);
    serviceRegistry.add("legacy_notification", makeLegacyNotificationService(legacyEnv));
    // deploy wowl services into the legacy env.
    const wowlToLegacyServiceMappers = registry.category("wowlToLegacyServiceMappers").getEntries();
    for (const [legacyServiceName, wowlToLegacyServiceMapper] of wowlToLegacyServiceMappers) {
        serviceRegistry.add(legacyServiceName, wowlToLegacyServiceMapper(legacyEnv));
    }
    // patch DebouncedField delay
    const debouncedField = basicFields.DebouncedField;
    const initialDebouncedVal = debouncedField.prototype.DEBOUNCE;
    debouncedField.prototype.DEBOUNCE = 0;
    registerCleanup(() => (debouncedField.prototype.DEBOUNCE = initialDebouncedVal));

    if (legacyParams.withLegacyMockServer) {
        const adapter = standaloneAdapter({ Component });
        registerCleanup(() => adapter.__owl__.app.destroy());
        adapter.env = legacyEnv;
        const W = Widget.extend({ do_push_state() {} });
        const widget = new W(adapter);
        const legacyMockServer = new LegacyMockServer(legacyParams.models, { widget });
        const originalRPC = env.services.rpc;
        const rpc = async (...args) => {
            try {
                return await originalRPC(...args);
            } catch (e) {
                if (e.message.includes("Unimplemented")) {
                    return legacyMockServer._performRpc(...args);
                } else {
                    throw e;
                }
            }
        };
        env.services.rpc = function () {
            let rejectFn;
            const rpcProm = new Promise((resolve, reject) => {
                rejectFn = reject;
                rpc(...arguments)
                    .then(resolve)
                    .catch(reject);
            });
            rpcProm.abort = () => rejectFn(new ConnectionAbortedError("XmlHttpRequestError abort"));
            return rpcProm;
        };
    }
}

/**
 * This method create a web client instance properly configured.
 *
 * Note that the returned web client will be automatically cleaned up after the
 * end of the test.
 *
 * @param {*} params
 */
export async function createWebClient(params) {
    setupWebClientRegistries();

    // With the compatibility layer, the action manager keeps legacy alive if they
    // are still acessible from the breacrumbs. They are manually destroyed as soon
    // as they are no longer referenced in the stack. This works fine in production,
    // because the webclient is never destroyed. However, at the end of each test,
    // we destroy the webclient and expect every legacy that has been instantiated
    // to be destroyed. We thus need to manually destroy them here.
    const controllers = [];
    patchWithCleanup(ClientActionAdapter.prototype, {
        setup() {
            this._super();
            onMounted(() => {
                controllers.push(this.widget);
            });
        },
    });
    patchWithCleanup(ViewAdapter.prototype, {
        setup() {
            this._super();
            onMounted(() => {
                controllers.push(this.widget);
            });
        },
    });

    const legacyParams = params.legacyParams;
    params.serverData = params.serverData || {};
    const models = params.serverData.models;
    if (legacyParams && legacyParams.withLegacyMockServer && models) {
        legacyParams.models = Object.assign({}, models);
        // In lagacy, data may not be sole models, but can contain some other variables
        // So we filter them out for our WOWL mockServer
        Object.entries(legacyParams.models).forEach(([k, v]) => {
            if (!(v instanceof Object) || !("fields" in v)) {
                delete models[k];
            }
        });
    }

    const mockRPC = params.mockRPC || undefined;
    const env = await makeTestEnv({
        serverData: params.serverData,
        mockRPC,
    });
    await addLegacyMockEnvironment(env, legacyParams);

    const WebClientClass = params.WebClientClass || WebClient;
    const target = params && params.target ? params.target : getFixture();
    const wc = await mount(WebClientClass, target, { env });
    target.classList.add("o_web_client"); // necessary for the stylesheet
    registerCleanup(() => {
        target.classList.remove("o_web_client");
        for (const controller of controllers) {
            if (!controller.isDestroyed()) {
                controller.destroy();
            }
        }
    });
    // Wait for visual changes caused by a potential loadState
    await nextTick();
    return wc;
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
    // wait the asynchronous hashchange
    // (the event hashchange must be triggered in a nonBlocking stack)
    await nextTick();
    // wait for the regular rendering
    await nextTick();
    // wait for the legacy rendering below owl layer
    await legacyExtraNextTick();
}

export function getActionManagerServerData() {
    // additional basic client action
    class TestClientAction extends Component {}
    TestClientAction.template = xml`
      <div class="test_client_action">
        ClientAction_<t t-esc="props.action.params?.description"/>
      </div>`;
    actionRegistry.add("__test__client__action__", TestClientAction);

    const menus = {
        root: { id: "root", children: [0, 1, 2], name: "root", appID: "root" },
        // id:0 is a hack to not load anything at webClient mount
        0: { id: 0, children: [], name: "UglyHack", appID: 0, xmlid: "menu_0" },
        1: { id: 1, children: [], name: "App1", appID: 1, actionID: 1001, xmlid: "menu_1" },
        2: { id: 2, children: [], name: "App2", appID: 2, actionID: 1002, xmlid: "menu_2" },
    };
    const actionsArray = [
        {
            id: 1,
            xml_id: "action_1",
            name: "Partners Action 1",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[1, "kanban"]],
        },
        {
            id: 2,
            xml_id: "action_2",
            type: "ir.actions.server",
        },
        {
            id: 3,
            xml_id: "action_3",
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
            xml_id: "action_4",
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
            xml_id: "action_5",
            name: "Create a Partner",
            res_model: "partner",
            target: "new",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        },
        {
            id: 6,
            xml_id: "action_6",
            name: "Partner",
            res_id: 2,
            res_model: "partner",
            target: "inline",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        },
        {
            id: 7,
            xml_id: "action_7",
            name: "Some Report",
            report_name: "some_report",
            report_type: "qweb-pdf",
            type: "ir.actions.report",
        },
        {
            id: 8,
            xml_id: "action_8",
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
            xml_id: "action_9",
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
            xml_id: "action_11",
            name: "Another Report",
            report_name: "another_report",
            report_type: "qweb-pdf",
            type: "ir.actions.report",
            close_on_report_download: true,
        },
        {
            id: 12,
            xml_id: "action_12",
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
            views: [[3, "form"]],
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
        "partner,3,form": `
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
        "partner,4,search":
            "<search>" +
            '<filter name="bar" help="Bar" domain="[(\'bar\', \'=\', 1)]"/>' +
            "</search>",
        "pony,false,search": "<search></search>",
    };
    const models = {
        partner: {
            fields: {
                id: { string: "Id", type: "integer" },
                foo: { string: "Foo", type: "char" },
                bar: { string: "Bar", type: "many2one", relation: "partner" },
                o2m: {
                    string: "One2Many",
                    type: "one2many",
                    relation: "partner",
                    relation_field: "bar",
                },
                m2o: { string: "Many2one", type: "many2one", relation: "partner" },
            },
            records: [
                { id: 1, display_name: "First record", foo: "yop", bar: 2, o2m: [2, 3], m2o: 3 },
                {
                    id: 2,
                    display_name: "Second record",
                    foo: "blip",
                    bar: 1,
                    o2m: [1, 4, 5],
                    m2o: 3,
                },
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
    return {
        models,
        views: archs,
        actions,
        menus,
    };
}
