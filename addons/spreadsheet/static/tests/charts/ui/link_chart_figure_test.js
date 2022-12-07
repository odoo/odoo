/** @odoo-module */

import { click, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { session } from "@web/session";
import { getBasicData } from "@spreadsheet/../tests/utils/data";
import { createBasicChart } from "@spreadsheet/../tests/utils/commands";
import { registry } from "@web/core/registry";
import { menuService } from "@web/webclient/menus/menu_service";
import { actionService } from "@web/webclient/actions/action_service";
import { ormService } from "@web/core/orm_service";
import { viewService } from "@web/views/view_service";
import { mountSpreadsheet } from "@spreadsheet/../tests/utils/ui";
import { createModelWithDataSource } from "@spreadsheet/../tests/utils/model";

const chartId = "uuid1";

/**
 * The chart menu is hidden by default, and visible on :hover, but this property
 * can't be triggered programmatically, so we artificially make it visible to be
 * able to interact with it.
 */
async function showChartMenu(fixture) {
    const chartMenu = fixture.querySelector(".o-figure-menu");
    chartMenu.style.display = "flex";
    await nextTick();
}

/** Click on external link of the first chart found in the page*/
async function clickChartExternalLink(fixture) {
    await showChartMenu(fixture);
    const chartMenuItem = fixture.querySelector(".o-figure-menu-item.o-chart-external-link");
    await click(chartMenuItem);
}

function mockActionService(assert, doActionStep) {
    const serviceRegistry = registry.category("services");
    serviceRegistry.add("actionMain", actionService);
    const fakeActionService = {
        dependencies: ["actionMain"],
        start(env, { actionMain }) {
            return {
                ...actionMain,
                doAction: (actionRequest, options = {}) => {
                    if (actionRequest === "menuAction2") {
                        assert.step(doActionStep);
                    }
                    return actionMain.doAction(actionRequest, options);
                },
            };
        },
    };
    serviceRegistry.add("action", fakeActionService, {
        force: true,
    });
}

QUnit.module(
    "spreadsheet > ir.ui.menu chart figure",
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
            patchWithCleanup(session, { uid: 1 });
            registry.category("services").add("menu", menuService).add("action", actionService);
            registry.category("services").add("view", viewService, { force: true }); // #action-serv-leg-compat-js-class
            registry.category("services").add("orm", ormService, { force: true }); // #action-serv-leg-compat-js-class
        },
    },

    () => {
        QUnit.test(
            "icon external link isn't on the chart when its not linked to an odoo menu",
            async function (assert) {
                const model = await createModelWithDataSource({
                    serverData: this.serverData,
                });
                const fixture = await mountSpreadsheet(model);
                createBasicChart(model, chartId);
                await nextTick();
                const odooMenu = model.getters.getChartOdooMenu(chartId);
                assert.equal(odooMenu, undefined, "No menu linked with the chart");

                const externalRefIcon = fixture.querySelector(".o-chart-external-link");
                assert.equal(externalRefIcon, null);
            }
        );

        QUnit.test(
            "icon external link is on the chart when its linked to an odoo menu",
            async function (assert) {
                const model = await createModelWithDataSource({
                    serverData: this.serverData,
                });
                const fixture = await mountSpreadsheet(model);
                createBasicChart(model, chartId);
                model.dispatch("LINK_ODOO_MENU_TO_CHART", {
                    chartId,
                    odooMenuId: 1,
                });
                const chartMenu = model.getters.getChartOdooMenu(chartId);
                assert.equal(chartMenu.id, 1, "Odoo menu is linked to chart");
                await nextTick();
                const externalRefIcon = fixture.querySelector(".o-chart-external-link");
                assert.ok(externalRefIcon);
            }
        );

        QUnit.test(
            "icon external link is not on the chart when its linked to a wrong odoo menu",
            async function (assert) {
                const model = await createModelWithDataSource({
                    serverData: this.serverData,
                });
                const fixture = await mountSpreadsheet(model);
                createBasicChart(model, chartId);
                model.dispatch("LINK_ODOO_MENU_TO_CHART", {
                    chartId,
                    odooMenuId: "menu which does not exist",
                });
                const chartMenu = model.getters.getChartOdooMenu(chartId);
                assert.equal(chartMenu, undefined, "cannot get a wrong menu");
                await nextTick();
                assert.containsNone(fixture, ".o-chart-external-link");
            }
        );

        QUnit.test(
            "icon external link isn't on the chart in dashboard mode",
            async function (assert) {
                const model = await createModelWithDataSource({
                    serverData: this.serverData,
                });
                const fixture = await mountSpreadsheet(model);
                createBasicChart(model, chartId);
                model.dispatch("LINK_ODOO_MENU_TO_CHART", {
                    chartId,
                    odooMenuId: 1,
                });
                const chartMenu = model.getters.getChartOdooMenu(chartId);
                assert.equal(chartMenu.id, 1, "Odoo menu is linked to chart");
                model.updateMode("dashboard");
                await nextTick();
                assert.containsNone(fixture, ".o-chart-external-link", "No link icon in dashboard");
            }
        );

        QUnit.test(
            "click on icon external link on chart redirect to the odoo menu",
            async function (assert) {
                const doActionStep = "doAction";
                mockActionService(assert, doActionStep);

                const model = await createModelWithDataSource({
                    serverData: this.serverData,
                });
                const fixture = await mountSpreadsheet(model);

                createBasicChart(model, chartId);
                model.dispatch("LINK_ODOO_MENU_TO_CHART", {
                    chartId,
                    odooMenuId: 2,
                });
                const chartMenu = model.getters.getChartOdooMenu(chartId);
                assert.equal(chartMenu.id, 2, "Odoo menu is linked to chart");
                await nextTick();

                await clickChartExternalLink(fixture);

                assert.verifySteps([doActionStep]);
            }
        );

        QUnit.test(
            "Click on chart in dashboard mode redirect to the odoo menu",
            async function (assert) {
                const doActionStep = "doAction";
                mockActionService(assert, doActionStep);
                const model = await createModelWithDataSource({
                    serverData: this.serverData,
                });
                const fixture = await mountSpreadsheet(model);

                createBasicChart(model, chartId);
                model.dispatch("LINK_ODOO_MENU_TO_CHART", {
                    chartId,
                    odooMenuId: 2,
                });
                const chartMenu = model.getters.getChartOdooMenu(chartId);
                assert.equal(chartMenu.id, 2, "Odoo menu is linked to chart");
                await nextTick();

                await click(fixture, ".o-chart-container");
                assert.verifySteps([], "Clicking on a chart while not dashboard mode do nothing");

                model.updateMode("dashboard");
                await nextTick();
                await click(fixture, ".o-chart-container");
                assert.verifySteps(
                    [doActionStep],
                    "Clicking on a chart while on dashboard mode redirect to the odoo menu"
                );
            }
        );

        QUnit.test("can use menus xmlIds instead of menu ids", async function (assert) {
            const serviceRegistry = registry.category("services");
            serviceRegistry.add("actionMain", actionService);
            const fakeActionService = {
                dependencies: ["actionMain"],
                start(env, { actionMain }) {
                    return {
                        ...actionMain,
                        doAction: (actionRequest, options = {}) => {
                            if (actionRequest === "menuAction2") {
                                assert.step("doAction");
                            }
                            return actionMain.doAction(actionRequest, options);
                        },
                    };
                },
            };
            serviceRegistry.add("action", fakeActionService, {
                force: true,
            });

            const model = await createModelWithDataSource({
                serverData: this.serverData,
            });
            const fixture = await mountSpreadsheet(model);

            createBasicChart(model, chartId);
            model.dispatch("LINK_ODOO_MENU_TO_CHART", {
                chartId,
                odooMenuId: "documents_spreadsheet.test.menu2",
            });
            await nextTick();

            await clickChartExternalLink(fixture);

            assert.verifySteps(["doAction"]);
        });
    }
);
