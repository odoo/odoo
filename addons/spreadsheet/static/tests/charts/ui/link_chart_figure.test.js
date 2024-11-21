import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { expect, test, beforeEach } from "@odoo/hoot";
import { getBasicData, defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { createBasicChart } from "@spreadsheet/../tests/helpers/commands";
import { mountSpreadsheet } from "@spreadsheet/../tests/helpers/ui";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";
import { mockService, serverState } from "@web/../tests/web_test_helpers";

defineSpreadsheetModels();

/**
 * @typedef {import("@spreadsheet/../tests/helpers/data").ServerData} ServerData
 */

const chartId = "uuid1";
let serverData = /** @type {ServerData} */ ({});

/**
 * The chart menu is hidden by default, and visible on :hover, but this property
 * can't be triggered programmatically, so we artificially make it visible to be
 * able to interact with it.
 */
async function showChartMenu(fixture) {
    const chartMenu = fixture.querySelector(".o-figure-menu");
    chartMenu.style.display = "flex";
    await animationFrame();
}

/** Click on external link of the first chart found in the page*/
async function clickChartExternalLink(fixture) {
    await showChartMenu(fixture);
    const chartMenuItem = fixture.querySelector(".o-figure-menu-item.o-chart-external-link");
    await click(chartMenuItem);
    await animationFrame();
}

function mockActionService(doActionStep) {
    const fakeActionService = {
        doAction: async (actionRequest, options = {}) => {
            if (actionRequest === "menuAction2") {
                expect.step(doActionStep);
            }
        },
    };
    mockService("action", fakeActionService);
}

beforeEach(async () => {
    serverData = {};
    serverData.menus = {
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
        3: {
            id: 3,
            children: [],
            name: "test menu 2",
            xmlid: "documents_spreadsheet.test.menu_without_action",
            appID: 1,
        },
    };
    serverData.actions = {
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
    serverData.models = {
        ...getBasicData(),
        "ir.ui.menu": {
            records: [
                { id: 1, name: "test menu 1", action: "action1", groups_id: [10] },
                { id: 2, name: "test menu 2", action: "action2", groups_id: [10] },
            ],
        },
        "res.group": { records: [{ id: 10, name: "test group" }] },
        "res.users": {
            records: [{ id: 1, active: true, partner_id: serverState.partnerId, name: "Raoul" }],
        },
        "ir.actions": { records: [{ id: 1 }] },
    };
    serverState.userId = 1;
});

test("icon external link isn't on the chart when its not linked to an odoo menu", async function () {
    const model = await createModelWithDataSource({
        serverData,
    });
    const fixture = await mountSpreadsheet(model);
    createBasicChart(model, chartId);
    await animationFrame();
    const odooMenu = model.getters.getChartOdooMenu(chartId);
    expect(odooMenu).toBe(undefined, { message: "No menu linked with the chart" });

    const externalRefIcon = fixture.querySelector(".o-chart-external-link");
    expect(externalRefIcon).toBe(null);
});

test("icon external link is on the chart when its linked to an odoo menu", async function () {
    const model = await createModelWithDataSource({
        serverData,
    });
    await mountSpreadsheet(model);
    createBasicChart(model, chartId);
    model.dispatch("LINK_ODOO_MENU_TO_CHART", {
        chartId,
        odooMenuId: 1,
    });

    const chartMenu = model.getters.getChartOdooMenu(chartId);
    expect(chartMenu.id).toBe(1, { message: "Odoo menu is linked to chart" });
    await animationFrame();
    expect(".o-chart-external-link").toHaveCount(1);
});

test("icon external link is not on the chart when its linked to a wrong odoo menu", async function () {
    const model = await createModelWithDataSource({
        serverData,
    });
    await mountSpreadsheet(model);
    createBasicChart(model, chartId);
    model.dispatch("LINK_ODOO_MENU_TO_CHART", {
        chartId,
        odooMenuId: "menu which does not exist",
    });
    const chartMenu = model.getters.getChartOdooMenu(chartId);
    expect(chartMenu).toBe(undefined, { message: "cannot get a wrong menu" });
    await animationFrame();
    expect(".o-chart-external-link").toHaveCount(0);
});

test("icon external link isn't on the chart in dashboard mode", async function () {
    const model = await createModelWithDataSource({
        serverData,
    });
    await mountSpreadsheet(model);
    createBasicChart(model, chartId);
    model.dispatch("LINK_ODOO_MENU_TO_CHART", {
        chartId,
        odooMenuId: 1,
    });
    const chartMenu = model.getters.getChartOdooMenu(chartId);
    expect(chartMenu.id).toBe(1, { message: "Odoo menu is linked to chart" });
    model.updateMode("dashboard");
    await animationFrame();
    expect(".o-chart-external-link").toHaveCount(0, { message: "No link icon in dashboard" });
});

test("click on icon external link on chart redirect to the odoo menu", async function () {
    const doActionStep = "doAction";
    mockActionService(doActionStep);

    const model = await createModelWithDataSource({
        serverData,
    });
    const fixture = await mountSpreadsheet(model);

    createBasicChart(model, chartId);
    model.dispatch("LINK_ODOO_MENU_TO_CHART", {
        chartId,
        odooMenuId: 2,
    });
    const chartMenu = model.getters.getChartOdooMenu(chartId);
    expect(chartMenu.id).toBe(2, { message: "Odoo menu is linked to chart" });
    await animationFrame();

    await clickChartExternalLink(fixture);

    expect.verifySteps([doActionStep]);
});

test("Click on chart in dashboard mode redirect to the odoo menu", async function () {
    const doActionStep = "doAction";
    mockActionService(doActionStep);
    const model = await createModelWithDataSource({
        serverData,
    });
    const fixture = await mountSpreadsheet(model);

    createBasicChart(model, chartId);
    model.dispatch("LINK_ODOO_MENU_TO_CHART", {
        chartId,
        odooMenuId: 2,
    });
    const chartMenu = model.getters.getChartOdooMenu(chartId);
    expect(chartMenu.id).toBe(2, { message: "Odoo menu is linked to chart" });
    await animationFrame();

    await click(fixture.querySelector(".o-chart-container"));
    await animationFrame();
    // Clicking on a chart while not dashboard mode do nothing
    expect.verifySteps([]);

    model.updateMode("dashboard");
    await animationFrame();
    await click(fixture.querySelector(".o-chart-container"));
    await animationFrame();
    // Clicking on a chart while on dashboard mode redirect to the odoo menu
    expect.verifySteps([doActionStep]);
});

test("can use menus xmlIds instead of menu ids", async function () {
    mockActionService("doAction");
    const model = await createModelWithDataSource({
        serverData,
    });
    const fixture = await mountSpreadsheet(model);

    createBasicChart(model, chartId);
    model.dispatch("LINK_ODOO_MENU_TO_CHART", {
        chartId,
        odooMenuId: "documents_spreadsheet.test.menu2",
    });
    await animationFrame();

    await clickChartExternalLink(fixture);

    expect.verifySteps(["doAction"]);
});

test("Trying to open a menu without an action sends a notification to the user", async function () {
    mockActionService("doAction");
    mockService("notification", {
        add: (message) => {
            expect.step(message);
            return () => {};
        },
    });

    const model = await createModelWithDataSource({
        serverData,
    });
    const fixture = await mountSpreadsheet(model);

    createBasicChart(model, chartId);
    model.dispatch("LINK_ODOO_MENU_TO_CHART", {
        chartId,
        odooMenuId: "documents_spreadsheet.test.menu_without_action",
    });
    await animationFrame();

    await clickChartExternalLink(fixture);

    const expectedNotificationMessage =
        "The menu linked to this chart doesn't have an corresponding action. Please link the chart to another menu.";
    // Notification was send and doAction wasn't called
    expect.verifySteps([expectedNotificationMessage]);
});
