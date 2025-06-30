/** @odoo-module alias=@web/../tests/webclient/helpers default=false */

import { dialogService } from "@web/core/dialog/dialog_service";
import { notificationService } from "@web/core/notifications/notification_service";
import { ormService } from "@web/core/orm_service";
import { popoverService } from "@web/core/popover/popover_service";
import { registry } from "@web/core/registry";
import { viewService } from "@web/views/view_service";
import { actionService } from "@web/webclient/actions/action_service";
import { effectService } from "@web/core/effects/effect_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { menuService } from "@web/webclient/menus/menu_service";
import { WebClient } from "@web/webclient/webclient";
import { registerCleanup } from "../helpers/cleanup";
import { makeTestEnv } from "../helpers/mock_env";
import {
    fakeTitleService,
    makeFakePwaService,
    makeFakeLocalizationService,
    makeFakeHTTPService,
    makeFakeBarcodeService,
} from "../helpers/mock_services";
import { getFixture, mount, nextTick } from "../helpers/utils";
import { uiService } from "@web/core/ui/ui_service";
import { commandService } from "@web/core/commands/command_service";
import { CustomFavoriteItem } from "@web/search/custom_favorite_item/custom_favorite_item";
import { overlayService } from "@web/core/overlay/overlay_service";

import { Component, onMounted, xml } from "@odoo/owl";
import { fieldService } from "@web/core/field_service";
import { nameService } from "@web/core/name_service";
import { datetimePickerService } from "@web/core/datetime/datetimepicker_service";
import { treeProcessorService } from "@web/core/tree_editor/tree_processor";

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
        barcode: () => makeFakeBarcodeService(),
        command: () => commandService,
        dialog: () => dialogService,
        effect: () => effectService,
        field: () => fieldService,
        tree_processor: () => treeProcessorService,
        hotkey: () => hotkeyService,
        http: () => makeFakeHTTPService(),
        pwa: () => makeFakePwaService(),
        localization: () => makeFakeLocalizationService(),
        menu: () => menuService,
        name: () => nameService,
        notification: () => notificationService,
        orm: () => ormService,
        overlay: () => overlayService,
        popover: () => popoverService,
        title: () => fakeTitleService,
        ui: () => uiService,
        view: () => viewService,
        datetime_picker: () => datetimePickerService,
    };
    for (const serviceName in services) {
        if (!serviceRegistry.contains(serviceName)) {
            serviceRegistry.add(serviceName, services[serviceName]());
        }
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

    params.serverData = params.serverData || {};
    const mockRPC = params.mockRPC || undefined;
    const env = await makeTestEnv({
        serverData: params.serverData,
        mockRPC,
    });

    const WebClientClass = params.WebClientClass || WebClient;
    const target = params && params.target ? params.target : getFixture();
    const wc = await mount(WebClientClass, target, { env });
    odoo.__WOWL_DEBUG__ = { root: wc };
    target.classList.add("o_web_client"); // necessary for the stylesheet
    registerCleanup(() => {
        target.classList.remove("o_web_client");
    });
    // Wait for visual changes caused by a potential loadState
    await nextTick();
    // wait for BlankComponent
    await nextTick();
    // wait for the regular rendering
    await nextTick();
    return wc;
}

export function doAction(env, ...args) {
    if (env instanceof Component) {
        env = env.env;
    }
    return env.services.action.doAction(...args);
}

export function getActionManagerServerData() {
    // additional basic client action
    class TestClientAction extends Component {
        static template = xml`
            <div class="test_client_action">
                ClientAction_<t t-esc="props.action.params?.description"/>
            </div>`;
        static props = ["*"];
        setup() {
            onMounted(() =>
                this.env.config.setDisplayName(`Client action ${this.props.action.id}`)
            );
        }
    }
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
            mobile_view_mode: "kanban",
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
            id: 26,
            xml_id: "action_26",
            name: "Partner",
            res_model: "partner",
            target: "new",
            type: "ir.actions.act_window",
            views: [[false, "list"]],
        },
        {
            id: 27,
            xml_id: "action_27",
            name: "Partners Action 27",
            res_model: "partner",
            mobile_view_mode: "kanban",
            type: "ir.actions.act_window",
            path: "partners",
            views: [
                [false, "list"],
                [1, "kanban"],
                [false, "form"],
            ],
        },
        {
            id: 28,
            xml_id: "action_28",
            name: "Partners Action 28",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [1, "kanban"],
                [2, "list"],
                [false, "form"],
            ],
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
            '<kanban><templates><t t-name="card">' +
            '<field name="foo"/>' +
            "</t></templates></kanban>",
        // list views
        "partner,false,list": '<list><field name="foo"/></list>',
        "partner,2,list": '<list limit="3"><field name="foo"/></list>',
        "pony,false,list": '<list><field name="name"/></list>',
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
      <div class="oe_button_box" name="button_box">
      <button class="oe_stat_button" type="action" name="1" icon="fa-star" context="{'default_partner': id}">
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
