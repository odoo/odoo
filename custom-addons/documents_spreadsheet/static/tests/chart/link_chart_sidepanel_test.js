/** @odoo-module */

import {
    click,
    editInput,
    getFixture,
    nextTick,
    patchWithCleanup,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import { session } from "@web/session";
import { createSpreadsheet } from "../spreadsheet_test_utils";
import { getBasicData } from "@spreadsheet/../tests/utils/data";
import {
    createBasicChart,
    createGaugeChart,
    createScorecardChart,
} from "@spreadsheet/../tests/utils/commands";
import { registry } from "@web/core/registry";
import { menuService } from "@web/webclient/menus/menu_service";
import { actionService } from "@web/webclient/actions/action_service";

let target;
const chartId = "uuid1";

/**
 * The chart menu is hidden by default, and visible on :hover, but this property
 * can't be triggered programmatically, so we artificially make it visible to be
 * able to interact with it.
 */
async function showChartMenu() {
    const chart = target.querySelector(".o-chart-container");
    const { x, y } = chart.getBoundingClientRect();
    await triggerEvent(chart, null, "contextmenu", { clientX: x, clientY: y });
}

/** Open the chart side panel of the first chart found in the page*/
async function openChartSidePanel() {
    await showChartMenu();
    await click(target, ".o-menu-item[title='Edit']");
}

QUnit.module(
    "documents_spreadsheet > ir.ui.menu chart ui",
    {
        beforeEach: function () {
            target = getFixture();
            this.serverData = {};
            this.serverData.menus = {
                root: {
                    id: "root",
                    children: [3],
                    name: "root",
                    appID: "root",
                },
                3: {
                    id: 3,
                    children: [1, 2],
                    name: "MyApp",
                    xmlid: "documents_spreadsheet.test.app",
                    appID: 3,
                    actionID: "menuAction",
                },
                1: {
                    id: 1,
                    children: [],
                    name: "test menu 1",
                    xmlid: "documents_spreadsheet.test.menu",
                    appID: 3,
                    actionID: "menuAction",
                },
                2: {
                    id: 2,
                    children: [],
                    name: "test menu 2",
                    xmlid: "documents_spreadsheet.test.menu2",
                    appID: 3,
                    actionID: "menuAction2",
                },
            };
            this.serverData.actions = {
                menuAction: {
                    id: 99,
                    xml_id: "ir.ui.menu",
                    name: "menuAction",
                    res_model: "ir.ui.menu",
                    type: "ir.actions.act_window",
                    views: [[false, "list"]],
                },
                menuAction2: {
                    id: 100,
                    xml_id: "ir.ui.menu",
                    name: "menuAction2",
                    res_model: "ir.ui.menu",
                    type: "ir.actions.act_window",
                    views: [[false, "list"]],
                },
            };
            this.serverData.views = {};
            this.serverData.views["ir.ui.menu,false,list"] = `<tree></tree>`;
            this.serverData.views["ir.ui.menu,false,search"] = `<search></search>`;
            this.serverData.models = {
                ...getBasicData(),
                "ir.ui.menu": {
                    fields: {
                        name: { string: "Name", type: "char" },
                        action: { string: "Action", type: "char" },
                        groups_id: {
                            string: "Groups",
                            type: "many2many",
                            relation: "res.group",
                        },
                    },
                    records: [
                        {
                            id: 1,
                            name: "test menu 1",
                            action: "action1",
                            groups_id: [10],
                        },
                        {
                            id: 2,
                            name: "test menu 2",
                            action: "action2",
                            groups_id: [10],
                        },
                    ],
                },
                "res.users": {
                    fields: {
                        name: { string: "Name", type: "char" },
                        groups_id: {
                            string: "Groups",
                            type: "many2many",
                            relation: "res.group",
                        },
                    },
                    records: [{ id: 1, name: "Raoul", groups_id: [10] }],
                },
                "ir.actions": {
                    fields: {
                        name: { string: "Name", type: "char" },
                    },
                    records: [{ id: 1 }],
                },
                "res.group": {
                    fields: { name: { string: "Name", type: "char" } },
                    records: [{ id: 10, name: "test group" }],
                },
            };
            patchWithCleanup(session, { uid: 1 });
            registry.category("services").add("menu", menuService).add("action", actionService);
        },
    },

    () => {
        QUnit.test(
            "can link an odoo menu to a basic chart chart in the side panel",
            async function (assert) {
                const { model } = await createSpreadsheet({
                    serverData: this.serverData,
                });
                createBasicChart(model, chartId);
                await nextTick();
                await openChartSidePanel();
                let odooMenu = model.getters.getChartOdooMenu(chartId);
                assert.equal(odooMenu, undefined, "No menu linked with chart at start");

                const irMenuField = target.querySelector(".o-ir-menu-selector input");
                assert.ok(
                    irMenuField,
                    "A menu to link charts to odoo menus was added to the side panel"
                );
                await click(irMenuField);
                await editInput(irMenuField, null, "");
                await click(document.querySelectorAll(".ui-menu-item")[0]);
                odooMenu = model.getters.getChartOdooMenu(chartId);
                assert.equal(
                    odooMenu.xmlid,
                    "documents_spreadsheet.test.menu",
                    "Odoo menu is linked to chart"
                );
            }
        );

        QUnit.test(
            "can link an odoo menu to a scorecard chart chart in the side panel",
            async function (assert) {
                const { model } = await createSpreadsheet({
                    serverData: this.serverData,
                });
                createScorecardChart(model, chartId);
                await nextTick();
                await openChartSidePanel();
                let odooMenu = model.getters.getChartOdooMenu(chartId);
                assert.equal(odooMenu, undefined, "No menu linked with chart at start");

                const irMenuField = target.querySelector(".o-ir-menu-selector input");
                assert.ok(
                    irMenuField,
                    "A menu to link charts to odoo menus was added to the side panel"
                );
                await click(irMenuField);
                await editInput(irMenuField, null, "");
                await click(document.querySelectorAll(".ui-menu-item")[0]);
                odooMenu = model.getters.getChartOdooMenu(chartId);
                assert.equal(
                    odooMenu.xmlid,
                    "documents_spreadsheet.test.menu",
                    "Odoo menu is linked to chart"
                );
            }
        );

        QUnit.test(
            "can link an odoo menu to a gauge chart chart in the side panel",
            async function (assert) {
                const { model } = await createSpreadsheet({
                    serverData: this.serverData,
                });
                createGaugeChart(model, chartId);
                await nextTick();
                await openChartSidePanel();
                let odooMenu = model.getters.getChartOdooMenu(chartId);
                assert.equal(odooMenu, undefined, "No menu linked with chart at start");

                const irMenuField = target.querySelector(".o-ir-menu-selector input");
                assert.ok(
                    irMenuField,
                    "A menu to link charts to odoo menus was added to the side panel"
                );
                await click(irMenuField);
                await editInput(irMenuField, null, "");
                await click(document.querySelectorAll(".ui-menu-item")[0]);
                odooMenu = model.getters.getChartOdooMenu(chartId);
                assert.equal(
                    odooMenu.xmlid,
                    "documents_spreadsheet.test.menu",
                    "Odoo menu is linked to chart"
                );
            }
        );

        QUnit.test(
            "can remove link between an odoo menu and a chart in the side panel",
            async function (assert) {
                const { model } = await createSpreadsheet({
                    serverData: this.serverData,
                });
                createBasicChart(model, chartId);
                await nextTick();
                model.dispatch("LINK_ODOO_MENU_TO_CHART", {
                    chartId,
                    odooMenuId: "documents_spreadsheet.test.menu",
                });
                await openChartSidePanel();
                await nextTick();
                const irMenuField = target.querySelector(".o-ir-menu-selector input");
                await editInput(irMenuField, null, "");
                await nextTick();
                const odooMenu = model.getters.getChartOdooMenu(chartId);
                assert.equal(odooMenu, undefined, "no menu is linked to chart");
            }
        );

        QUnit.test(
            "Linked menu change in the side panel when we select another chart",
            async function (assert) {
                const { model } = await createSpreadsheet({
                    serverData: this.serverData,
                });
                const chartId2 = "id2";
                createBasicChart(model, chartId);
                createBasicChart(model, chartId2);
                await nextTick();
                model.dispatch("LINK_ODOO_MENU_TO_CHART", {
                    chartId,
                    odooMenuId: 1,
                });
                model.dispatch("LINK_ODOO_MENU_TO_CHART", {
                    chartId: chartId2,
                    odooMenuId: 2,
                });
                await openChartSidePanel();
                await nextTick();

                let irMenuInput = target.querySelector(".o-ir-menu-selector input");
                assert.equal(irMenuInput.value, "MyApp/test menu 1");

                const figure2 = target.querySelectorAll(".o-figure")[1];
                // click() doesn't work, I guess because we are using the mousedown event on figures and not the click
                const clickEvent = new Event("mousedown", { bubbles: true });
                figure2.dispatchEvent(clickEvent);
                await nextTick();
                irMenuInput = target.querySelector(".o-ir-menu-selector input");
                assert.equal(irMenuInput.value, "MyApp/test menu 2");
            }
        );
    }
);
