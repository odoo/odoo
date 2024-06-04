/** @odoo-module */

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { getBasicData } from "@spreadsheet/../tests/utils/data";
import { createBasicChart } from "@spreadsheet/../tests/utils/commands";
import { createSpreadsheetWithChart } from "@spreadsheet/../tests/utils/chart";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { registry } from "@web/core/registry";
import { menuService } from "@web/webclient/menus/menu_service";
import { actionService } from "@web/webclient/actions/action_service";
import { ormService } from "@web/core/orm_service";
import { viewService } from "@web/views/view_service";

const { Model } = spreadsheet;

const chartId = "uuid1";

QUnit.module(
    "spreadsheet > ir.ui.menu chart plugin",
    {
        beforeEach: function () {
            this.serverData = {};
            this.serverData.menus = {
                root: {
                    id: "root",
                    children: [1, 2],
                    name: "root",
                    appID: "root",
                },
                1: {
                    id: 1,
                    children: [],
                    name: "test menu 1",
                    xmlid: "documents_spreadsheet.test.menu",
                    appID: 1,
                    actionID: "menuAction",
                },
                2: {
                    id: 2,
                    children: [],
                    name: "test menu 2",
                    xmlid: "documents_spreadsheet.test.menu2",
                    appID: 1,
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
            registry.category("services").add("menu", menuService).add("action", actionService);
            registry.category("services").add("view", viewService, { force: true }); // #action-serv-leg-compat-js-class
            registry.category("services").add("orm", ormService, { force: true }); // #action-serv-leg-compat-js-class
        },
    },

    () => {
        QUnit.test(
            "Links between charts and ir.menus are correctly imported/exported",
            async function (assert) {
                const env = await makeTestEnv({ serverData: this.serverData });
                const model = new Model({}, { evalContext: { env } });
                createBasicChart(model, chartId);
                model.dispatch("LINK_ODOO_MENU_TO_CHART", {
                    chartId,
                    odooMenuId: 1,
                });
                const exportedData = model.exportData();
                assert.equal(
                    exportedData.chartOdooMenusReferences[chartId],
                    1,
                    "Link to odoo menu is exported"
                );
                const importedModel = new Model(exportedData, { evalContext: { env } });
                const chartMenu = importedModel.getters.getChartOdooMenu(chartId);
                assert.equal(chartMenu.id, 1, "Link to odoo menu is imported");
            }
        );

        QUnit.test("Can undo-redo a LINK_ODOO_MENU_TO_CHART", async function (assert) {
            const env = await makeTestEnv({ serverData: this.serverData });
            const model = new Model({}, { evalContext: { env } });
            createBasicChart(model, chartId);
            model.dispatch("LINK_ODOO_MENU_TO_CHART", {
                chartId,
                odooMenuId: 1,
            });
            assert.equal(model.getters.getChartOdooMenu(chartId).id, 1);
            model.dispatch("REQUEST_UNDO");
            assert.equal(model.getters.getChartOdooMenu(chartId), undefined);
            model.dispatch("REQUEST_REDO");
            assert.equal(model.getters.getChartOdooMenu(chartId).id, 1);
        });

        QUnit.test("link is removed when figure is deleted", async function (assert) {
            const env = await makeTestEnv({ serverData: this.serverData });
            const model = new Model({}, { evalContext: { env } });
            createBasicChart(model, chartId);
            model.dispatch("LINK_ODOO_MENU_TO_CHART", {
                chartId,
                odooMenuId: 1,
            });
            assert.equal(model.getters.getChartOdooMenu(chartId).id, 1);
            model.dispatch("DELETE_FIGURE", {
                sheetId: model.getters.getActiveSheetId(),
                id: chartId,
            });
            assert.equal(model.getters.getChartOdooMenu(chartId), undefined);
        });

        QUnit.test(
            "Links of Odoo charts are duplicated when duplicating a sheet",
            async function (assert) {
                const { model } = await createSpreadsheetWithChart({
                    type: "odoo_pie",
                    serverData: this.serverData,
                });
                const sheetId = model.getters.getActiveSheetId();
                const secondSheetId = "mySecondSheetId";
                const chartId = model.getters.getChartIds(sheetId)[0];
                model.dispatch("DUPLICATE_SHEET", { sheetId, sheetIdTo: secondSheetId });
                const newChartId = model.getters.getChartIds(secondSheetId)[0];
                assert.deepEqual(
                    model.getters.getChartOdooMenu(newChartId),
                    model.getters.getChartOdooMenu(chartId)
                );
            }
        );

        QUnit.test(
            "Links of standard charts are duplicated when duplicating a sheet",
            async function (assert) {
                const env = await makeTestEnv({ serverData: this.serverData });
                const model = new Model({}, { evalContext: { env } });
                const sheetId = model.getters.getActiveSheetId();
                const secondSheetId = "mySecondSheetId";
                createBasicChart(model, chartId);
                model.dispatch("LINK_ODOO_MENU_TO_CHART", {
                    chartId,
                    odooMenuId: 1,
                });
                model.dispatch("DUPLICATE_SHEET", { sheetId, sheetIdTo: secondSheetId });
                const newChartId = model.getters.getChartIds(secondSheetId)[0];
                assert.deepEqual(
                    model.getters.getChartOdooMenu(newChartId),
                    model.getters.getChartOdooMenu(chartId)
                );
            }
        );
    }
);
