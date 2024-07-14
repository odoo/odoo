/** @odoo-module */

import { busService } from "@bus/services/bus_service";
import { busParametersService } from "@bus/bus_parameters_service";
import { multiTabService } from "@bus/multi_tab_service";

import { makeFakeUserService } from "@web/../tests/helpers/mock_services";
import {
    click,
    getFixture,
    nextTick,
    patchWithCleanup,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import { toggleSearchBarMenu, toggleMenu, toggleMenuItem } from "@web/../tests/search/helpers";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { getBasicData } from "@spreadsheet/../tests/utils/data";
import { registry } from "@web/core/registry";
import { InsertViewSpreadsheet } from "@spreadsheet_edition/assets/insert_action_link_menu/insert_action_link_menu";
import { spreadsheetLinkMenuCellService } from "@spreadsheet/ir_ui_menu/index";

import { loadJS } from "@web/core/assets";
import { makeFakeSpreadsheetService } from "@spreadsheet_edition/../tests/utils/collaborative_helpers";

const serviceRegistry = registry.category("services");
const favoriteMenuRegistry = registry.category("favoriteMenu");

import * as spreadsheet from "@odoo/o-spreadsheet";
const { Grid } = spreadsheet.components;

let serverData;
async function openView(viewType, options = {}) {
    favoriteMenuRegistry.add(
        "insert-action-link-in-spreadsheet",
        {
            Component: InsertViewSpreadsheet,
            groupNumber: 4,
            isDisplayed: ({ isSmall, config }) =>
                !isSmall && config.actionType === "ir.actions.act_window",
        },
        { sequence: 1 }
    );
    serviceRegistry.add("spreadsheet_collaborative", makeFakeSpreadsheetService());
    serviceRegistry.add("spreadsheetLinkMenuCell", spreadsheetLinkMenuCellService);
    const webClient = await createWebClient({
        serverData,
        mockRPC: options.mockRPC,
    });
    await doAction(webClient, 1, { viewType, additionalContext: options.additionalContext });
    return webClient;
}

async function insertInSpreadsheetAndClickLink(target) {
    await loadJS("/web/static/lib/Chart/Chart.js");
    patchWithCleanup(Grid.prototype, {
        setup() {
            super.setup();
            this.hoveredCell = { col: 0, row: 0 };
        },
    });
    // Open search bar menu if it is not already
    if (!target.querySelector(".o_search_bar_menu")) {
        await toggleSearchBarMenu(target);
    }
    await click(target, ".o_insert_action_spreadsheet_menu");
    await click(document, ".modal-footer button.btn-primary");
    await nextTick();
    await nextTick();
    await click(target, ".o-link-tool a");
    await nextTick();
}

function getCurrentViewType(webClient) {
    return webClient.env.services.action.currentController.view.type;
}

function getCurrentAction(webClient) {
    return webClient.env.services.action.currentController.action;
}

let target;
QUnit.module(
    "spreadsheet_edition > action link",
    {
        beforeEach: function () {
            target = getFixture();
            serverData = {};
            serverData.models = getBasicData();
            serverData.actions = {
                1: {
                    id: 1,
                    xml_id: "action_1",
                    name: "Partners Action 1",
                    res_model: "partner",
                    type: "ir.actions.act_window",
                    view_mode: "list",
                    views: [
                        [1, "list"],
                        [2, "kanban"],
                        [3, "graph"],
                        [4, "calendar"],
                        [5, "pivot"],
                        [6, "map"],
                    ],
                },
            };
            serverData.views = {
                "partner,1,list": '<tree><field name="foo"/></tree>',
                "partner,2,kanban": `<kanban><templates><t t-name="kanban-box"><field name="foo"/></t></templates></kanban>`,
                "partner,view_graph_xml_id,graph": /*xml*/ `
                    <graph>
                        <field name="probability" type="measure"/>
                    </graph>`,
                "partner,4,calendar": `<calendar date_start="date"></calendar>`,
                "partner,5,pivot": /*xml*/ `
                    <pivot>
                        <field name="bar" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>`,
                "partner,6,map": `<map></map>`,
                "partner,false,search": /*xml*/ `
                    <search>
                        <field name="foo"/>
                        <filter name="filter_1" domain="[['name', '=', 'Raoul']]"/>
                        <filter name="filter_2" domain="[['name', '=', False]]"/>
                        <filter name="group_by_name" context="{'group_by':'name'}"/>
                    </search>`,
            };
            serverData.models.partner.methods = {
                async check_access_rights() {
                    return true;
                },
            };
            registry.category("services").add("multi_tab", multiTabService);
            registry.category("services").add("bus.parameters", busParametersService);
            registry.category("services").add("bus_service", busService);
        },
    },
    () => {
        QUnit.test("simple list view", async function (assert) {
            const webClient = await openView("list");
            await insertInSpreadsheetAndClickLink(target);
            assert.strictEqual(getCurrentViewType(webClient), "list");
        });

        QUnit.test("list view with custom domain and groupby", async function (assert) {
            serverData.actions["1"].domain = [["id", "!=", 0]];
            const webClient = await openView("list", {
                additionalContext: { search_default_filter_2: 1 },
            });

            // add a domain
            await toggleSearchBarMenu(target);
            await toggleMenuItem(target.querySelector(".o_filter_menu"), 0);

            // group by name
            await toggleMenuItem(target.querySelector(".o_group_by_menu"), 0);

            await insertInSpreadsheetAndClickLink(target);
            assert.strictEqual(getCurrentViewType(webClient), "list");
            const action = getCurrentAction(webClient);
            assert.deepEqual(
                action.domain,
                ["&", ["id", "!=", 0], "|", ["name", "=", false], ["name", "=", "Raoul"]],
                "The domain should be the same"
            );
            assert.strictEqual(action.res_model, "partner");
            assert.strictEqual(action.type, "ir.actions.act_window");
            assert.deepEqual(action.context.group_by, ["name"], "It should be grouped by name");
            assert.containsOnce(target, ".o_group_header", "The list view should be grouped");
        });

        QUnit.test("insert list in existing spreadsheet", async function (assert) {
            await openView("list", {
                mockRPC: function (route, args) {
                    if (args.method === "join_spreadsheet_session") {
                        assert.step("spreadsheet-joined");
                        assert.equal(args.args[0], 1, "It should join the selected spreadsheet");
                    }
                },
            });
            await loadJS("/web/static/lib/Chart/Chart.js");
            await toggleSearchBarMenu(target);
            await click(target, ".o_insert_action_spreadsheet_menu");
            await triggerEvent(target, ".o-sp-dialog-item div[data-id='1']", "focus");
            await click(target, ".modal-footer button.btn-primary");
            await nextTick();
            assert.verifySteps(["spreadsheet-joined"]);
        });

        QUnit.test("insert action in new spreadsheet", async function (assert) {
            await openView("list", {
                mockRPC: async function (route, args) {
                    if (args.method === "action_open_new_spreadsheet") {
                        assert.step("spreadsheet-created");
                    }
                },
            });
            await loadJS("/web/static/lib/Chart/Chart.js");
            assert.containsNone(target, ".o_spreadsheet_action");
            await toggleSearchBarMenu(target);
            await click(target, ".o_insert_action_spreadsheet_menu");
            await click(target, ".modal-footer button.btn-primary");
            await nextTick();
            assert.verifySteps(["spreadsheet-created"]);
            assert.containsOnce(target, ".o_spreadsheet_action");
            assert.strictEqual(
                target.querySelector(".o_breadcrumb .o_spreadsheet_name input").value,
                "Untitled spreadsheet"
            );
        });

        QUnit.test("kanban view", async function (assert) {
            const webClient = await openView("kanban");
            await insertInSpreadsheetAndClickLink(target);
            assert.strictEqual(getCurrentViewType(webClient), "kanban");
        });

        QUnit.test("simple graph view", async function (assert) {
            serviceRegistry.add("user", makeFakeUserService());
            const webClient = await openView("graph");
            await insertInSpreadsheetAndClickLink(target);
            assert.strictEqual(getCurrentViewType(webClient), "graph");
        });

        QUnit.test("graph view with custom chart type and order", async function (assert) {
            serviceRegistry.add("user", makeFakeUserService());
            const webClient = await openView("graph");
            await click(target, ".fa-pie-chart");
            // count measure
            await toggleMenu(target, "Measures");
            await toggleMenuItem(target, "Count");
            await insertInSpreadsheetAndClickLink(target);
            const action = getCurrentAction(webClient);
            assert.deepEqual(action.context.graph_mode, "pie", "It should be a pie chart");
            assert.deepEqual(
                action.context.graph_measure,
                "__count",
                "It should have the custom measures"
            );
            assert.containsOnce(target, ".fa-pie-chart.active");
        });

        QUnit.test("calendar view", async function (assert) {
            const webClient = await openView("calendar");
            await insertInSpreadsheetAndClickLink(target);
            assert.strictEqual(getCurrentViewType(webClient), "calendar");
        });

        QUnit.test("simple pivot view", async function (assert) {
            serviceRegistry.add("user", makeFakeUserService());
            const webClient = await openView("pivot");
            await insertInSpreadsheetAndClickLink(target);
            assert.strictEqual(getCurrentViewType(webClient), "pivot");
        });

        QUnit.test("pivot view with custom group by and measure", async function (assert) {
            serviceRegistry.add("user", makeFakeUserService());
            const webClient = await openView("pivot");

            // group by name
            await toggleSearchBarMenu(target);
            await toggleMenuItem(target, "name");

            // add count measure
            await toggleMenu(target, "Measures");
            await toggleMenuItem(target, "Count");

            await insertInSpreadsheetAndClickLink(target);
            const action = getCurrentAction(webClient);

            assert.deepEqual(
                action.context.pivot_row_groupby,
                ["name"],
                "It should be grouped by name"
            );
            assert.deepEqual(
                action.context.pivot_measures,
                ["probability", "__count"],
                "It should have the same two measures"
            );
            assert.containsN(
                target,
                ".o_pivot_measure_row",
                2,
                "It should display the two measures"
            );
        });

        QUnit.test("map view", async function (assert) {
            const webClient = await openView("map");
            await insertInSpreadsheetAndClickLink(target);
            assert.strictEqual(getCurrentViewType(webClient), "map");
        });

        QUnit.test("action with domain being the empty string", async function (assert) {
            assert.expect(1);
            serverData.actions["1"].domain = "";
            const webClient = await openView("list");
            await insertInSpreadsheetAndClickLink(target);
            assert.strictEqual(getCurrentViewType(webClient), "list");
        });
    }
);
