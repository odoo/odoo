import {
    defineDocumentSpreadsheetModels,
    getBasicData,
} from "@documents_spreadsheet/../tests/helpers/data";
import { beforeEach, describe, expect, getFixture, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { contains, serverState } from "@web/../tests/web_test_helpers";
import { createSpreadsheet } from "@documents_spreadsheet/../tests/helpers/spreadsheet_test_utils";
import {
    createBasicChart,
    createGaugeChart,
    createScorecardChart,
} from "@spreadsheet/../tests/helpers/commands";
import { manuallyDispatchProgrammaticEvent } from "@odoo/hoot-dom";

defineDocumentSpreadsheetModels();
describe.current.tags("desktop");

let target;
let serverData;
const chartId = "uuid1";

/** Open the chart side panel of the first chart found in the page*/
async function openChartSidePanel() {
    await contains(".o-chart-container").click({ button: 2 });
    await contains(".o-menu-item[title='Edit']").click();
}

beforeEach(() => {
    target = getFixture();
    serverData = /** @type any */ ({});
    serverData.menus = {
        root: {
            id: "root",
            name: "root",
            appID: "root",
            children: [
                {
                    id: 3,
                    name: "MyApp",
                    xmlid: "documents_spreadsheet.test.app",
                    appID: 3,
                    actionID: "menuAction",
                    children: [
                        {
                            id: 1,
                            name: "test menu 1",
                            xmlid: "documents_spreadsheet.test.menu",
                            appID: 3,
                            actionID: "menuAction",
                        },
                        {
                            id: 2,
                            name: "test menu 2",
                            xmlid: "documents_spreadsheet.test.menu2",
                            appID: 3,
                            actionID: "menuAction2",
                        },
                    ],
                },
            ],
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
    serverData.views = {};
    serverData.models = {
        ...getBasicData(),
        "ir.ui.menu": {
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
            records: [
                {
                    id: 1,
                    name: "Raoul",
                    groups_id: [10],
                    partner_id: serverState.partnerId,
                    active: true,
                },
                { id: serverState.odoobotId, name: "OdooBot" },
            ],
        },
        "ir.actions": {
            records: [{ id: 1 }],
        },
        "res.group": {
            records: [{ id: 10, name: "test group" }],
        },
    };
    serverState.userId = 1;
});

test("can link an odoo menu to a basic chart chart in the side panel", async function () {
    const { model } = await createSpreadsheet({ serverData });
    createBasicChart(model, chartId);
    await animationFrame();
    await openChartSidePanel();
    let odooMenu = model.getters.getChartOdooMenu(chartId);
    expect(odooMenu).toBe(undefined, { message: "No menu linked with chart at start" });

    expect(".o-ir-menu-selector input").toHaveCount(1, {
        message: "A menu to link charts to odoo menus was added to the side panel",
    });
    await contains(".o-ir-menu-selector input").click();
    await contains(".ui-menu-item").click();
    odooMenu = model.getters.getChartOdooMenu(chartId);
    expect(odooMenu.xmlid).toBe("documents_spreadsheet.test.menu", {
        message: "Odoo menu is linked to chart",
    });
});

test("can link an odoo menu to a scorecard chart chart in the side panel", async function () {
    const { model } = await createSpreadsheet({ serverData });
    createScorecardChart(model, chartId);
    await animationFrame();
    await openChartSidePanel();
    let odooMenu = model.getters.getChartOdooMenu(chartId);
    expect(odooMenu).toBe(undefined, { message: "No menu linked with chart at start" });

    expect(".o-ir-menu-selector input").toHaveCount(1, {
        message: "A menu to link charts to odoo menus was added to the side panel",
    });
    await contains(".o-ir-menu-selector input").click();
    await contains(".ui-menu-item").click();
    odooMenu = model.getters.getChartOdooMenu(chartId);
    expect(odooMenu.xmlid).toBe("documents_spreadsheet.test.menu", {
        message: "Odoo menu is linked to chart",
    });
});

test("can link an odoo menu to a gauge chart chart in the side panel", async function () {
    const { model } = await createSpreadsheet({ serverData });
    createGaugeChart(model, chartId);
    await animationFrame();
    await openChartSidePanel();
    let odooMenu = model.getters.getChartOdooMenu(chartId);
    expect(odooMenu).toBe(undefined, { message: "No menu linked with chart at start" });

    const irMenuField = target.querySelector(".o-ir-menu-selector input");
    expect(".o-ir-menu-selector input").toHaveCount(1, {
        message: "A menu to link charts to odoo menus was added to the side panel",
    });
    await contains(irMenuField).click();
    await contains(".ui-menu-item").click();
    odooMenu = model.getters.getChartOdooMenu(chartId);
    expect(odooMenu.xmlid).toBe("documents_spreadsheet.test.menu", {
        message: "Odoo menu is linked to chart",
    });
});

test("can remove link between an odoo menu and a chart in the side panel", async function () {
    const { model } = await createSpreadsheet({ serverData });
    createBasicChart(model, chartId);
    await animationFrame();
    model.dispatch("LINK_ODOO_MENU_TO_CHART", {
        chartId,
        odooMenuId: "documents_spreadsheet.test.menu",
    });
    await openChartSidePanel();
    await animationFrame();
    const irMenuField = target.querySelector(".o-ir-menu-selector input");

    // edit() helper is not working on Many2XAutocomplete for whatever reason
    irMenuField.value = "";
    await manuallyDispatchProgrammaticEvent(irMenuField, "change");

    await animationFrame();
    const odooMenu = model.getters.getChartOdooMenu(chartId);
    expect(odooMenu).toBe(undefined, { message: "no menu is linked to chart" });
});

test("Linked menu change in the side panel when we select another chart", async function () {
    const { model } = await createSpreadsheet({ serverData });
    const chartId2 = "id2";
    createBasicChart(model, chartId);
    createBasicChart(model, chartId2);
    await animationFrame();
    model.dispatch("LINK_ODOO_MENU_TO_CHART", {
        chartId,
        odooMenuId: 1,
    });
    model.dispatch("LINK_ODOO_MENU_TO_CHART", {
        chartId: chartId2,
        odooMenuId: 2,
    });
    await openChartSidePanel();
    await animationFrame();

    let irMenuInput = target.querySelector(".o-ir-menu-selector input");
    expect(irMenuInput).toHaveValue("MyApp/test menu 1");

    const figure2 = target.querySelectorAll(".o-figure")[1];
    await contains(figure2).click();
    irMenuInput = target.querySelector(".o-ir-menu-selector input");
    expect(irMenuInput).toHaveValue("MyApp/test menu 2");
});
