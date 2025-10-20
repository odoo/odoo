import { beforeEach, expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { components } from "@odoo/o-spreadsheet";
import { insertChartInSpreadsheet } from "@spreadsheet/../tests/helpers/chart";
import {
    createBasicChart,
    createScorecardChart,
    createGaugeChart,
    addChartFigureToCarousel,
    createCarousel,
} from "@spreadsheet/../tests/helpers/commands";
import { getBasicData } from "@spreadsheet/../tests/helpers/data";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/helpers/pivot";
import { mountSpreadsheet } from "@spreadsheet/../tests/helpers/ui";
import { defineSpreadsheetDashboardModels } from "@spreadsheet_dashboard/../tests/helpers/data";
import { contains, mockService, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";

defineSpreadsheetDashboardModels();

/**
 * @typedef {import("@spreadsheet/../tests/helpers/data").ServerData} ServerData
 */

const chartId = "uuid1";
let serverData = /** @type {ServerData} */ ({});

function mockActionService(doActionStep) {
    const fakeActionService = {
        doAction: async (actionRequest, options = {}) => {
            if (actionRequest.xml_id === "menuAction2") {
                expect.step(doActionStep);
            }
        },
    };
    mockService("action", fakeActionService);
}

beforeEach(() => {
    serverData = {};
    serverData.menus = {
        2: {
            id: 2,
            name: "test menu 2",
            xmlid: "spreadsheet.test.menu2",
            appID: 1,
            actionID: "menuAction2",
        },
    };
    serverData.actions = {
        menuAction2: {
            id: 100,
            xml_id: "menuAction2",
            name: "menuAction2",
            res_model: "ir.ui.menu",
            type: "ir.actions.act_window",
            views: [[false, "list"]],
        },
    };
    serverData.models = {
        ...getBasicData(),
        "ir.ui.menu": {
            records: [{ id: 2, name: "test menu 2", action: "action2", group_ids: [10] }],
        },
        "res.group": { records: [{ id: 10, name: "test group" }] },
    };
});

test("Click on chart in dashboard mode redirect to the datasource action", async function () {
    const doActionStep = "doAction";
    mockActionService(doActionStep);
    const { model, pivotId } = await createSpreadsheetWithPivot({
        serverData,
        actionXmlId: "menuAction2",
    });
    const fixture = await mountSpreadsheet(model);

    createBasicChart(model, chartId);
    model.dispatch("UPDATE_ODOO_LINK_TO_CHART", {
        chartId,
        odooLink: { type: "dataSource", dataSourceType: "pivot", dataSourceCoreId: pivotId },
    });
    const chartMenu = model.getters.getChartOdooLink(chartId);
    expect(chartMenu).toEqual(
        { type: "dataSource", dataSourceType: "pivot", dataSourceCoreId: pivotId },
        { message: "Odoo menu is linked to chart" }
    );
    await animationFrame();

    await click(fixture.querySelector(".o-chart-container canvas"));
    await animationFrame();
    // Clicking on a chart while not dashboard mode do nothing
    expect.verifySteps([]);

    model.updateMode("dashboard");
    await animationFrame();
    await click(fixture.querySelector(".o-chart-container canvas"));
    await animationFrame();
    // Clicking on a chart while on dashboard mode redirect to the odoo menu
    expect.verifySteps([doActionStep]);
});

test("Click on chart element in dashboard mode do not redirect twice", async function () {
    patchWithCleanup(components.ChartJsComponent.prototype, {
        enableAnimationInChartData(chartData) {
            return chartData; // disable animation for the test
        },
    });

    mockService("action", {
        doAction: async (actionRequest, options = {}) => {
            if (
                actionRequest.type === "ir.actions.act_window" &&
                actionRequest.res_model === "partner"
            ) {
                if (actionRequest.xml_id === "menuAction2") {
                    expect.step("chartMenuRedirect");
                } else {
                    expect.step("chartElementRedirect"); // no relation to the related ds
                }
            }
        },
    });

    const { model, pivotId } = await createSpreadsheetWithPivot({
        serverData,
        actionXmlId: "menuAction2",
    });
    const fixture = await mountSpreadsheet(model);
    const chartId = insertChartInSpreadsheet(model, "odoo_pie");
    model.dispatch("UPDATE_ODOO_LINK_TO_CHART", {
        chartId,
        odooLink: { type: "dataSource", dataSourceType: "pivot", dataSourceCoreId: pivotId },
    });
    await animationFrame();
    model.updateMode("dashboard");
    await animationFrame();

    // Click pie element
    const chartCanvas = fixture.querySelector(".o-chart-container canvas");
    const canvasRect = chartCanvas.getBoundingClientRect();
    const canvasCenter = {
        x: canvasRect.left + canvasRect.width / 2 - 5,
        y: canvasRect.top + canvasRect.height / 2 - 5,
    };
    await click(".o-chart-container canvas", { position: canvasCenter, relative: true });
    await animationFrame();
    expect.verifySteps(["chartElementRedirect"]);

    // Click outside the pie element
    await click(".o-chart-container canvas", { position: "top-left" });
    await animationFrame();
    expect.verifySteps(["chartMenuRedirect"]);
});

test("Can click on a chart with no odoo link", async function () {
    const { model } = await createSpreadsheetWithPivot({ serverData });
    await mountSpreadsheet(model);
    createBasicChart(model, chartId);
    await animationFrame();

    model.updateMode("dashboard");
    await animationFrame();

    await contains(".o-chart-container canvas").click();
    await animationFrame();
    expect.verifySteps([]);
});

test("Clicking on a scorecard or gauge redirects to the linked datasource", async function () {
    mockService("action", {
        doAction: async (actionRequest) => expect.step(actionRequest.xml_id || "noId"),
    });

    const { model, pivotId } = await createSpreadsheetWithPivot({
        serverData,
        actionXmlId: "menuAction2",
    });
    await mountSpreadsheet(model);
    createScorecardChart(model, "scorecardId");
    createGaugeChart(model, "gaugeId");
    model.dispatch("UPDATE_ODOO_LINK_TO_CHART", {
        chartId: "scorecardId",
        odooLink: { type: "dataSource", dataSourceType: "pivot", dataSourceCoreId: pivotId },
    });
    model.dispatch("UPDATE_ODOO_LINK_TO_CHART", {
        chartId: "gaugeId",
        odooLink: { type: "dataSource", dataSourceType: "pivot", dataSourceCoreId: pivotId },
    });
    await animationFrame();

    model.updateMode("dashboard");
    await animationFrame();

    const chartCanvas = document.querySelectorAll(".o-figure canvas");

    await click(chartCanvas[0]);
    await animationFrame();
    expect.verifySteps(["menuAction2"]);

    await click(chartCanvas[1]);
    expect.verifySteps(["menuAction2"]);
});

test.tags("desktop");
test("Middle-click on chart in dashboard mode open the linked datasource in a new tab", async function () {
    const { model, pivotId } = await createSpreadsheetWithPivot({
        serverData,
        actionXmlId: "menuAction2",
    });
    await mountSpreadsheet(model);

    mockService("action", {
        doAction(_, options) {
            expect.step("doAction");
            expect(options).toMatchObject({
                newWindow: true,
            });
            return Promise.resolve(true);
        },
    });

    createBasicChart(model, chartId);
    model.dispatch("UPDATE_ODOO_LINK_TO_CHART", {
        chartId,
        odooLink: { type: "dataSource", dataSourceType: "pivot", dataSourceCoreId: pivotId },
    });

    model.updateMode("dashboard");
    await animationFrame();
    await contains(".o-chart-container canvas").click({ ctrlKey: true });
    expect.verifySteps(["doAction"]);

    await contains(".o-chart-container canvas").click({ button: 1 }); // middle mouse click
    expect.verifySteps(["doAction"]);
});

test("Clicking on the carousel header doesn't redirect to its chart's linked menu", async function () {
    mockService("action", {
        doAction: async (actionRequest) => expect.step(actionRequest),
    });

    const { model } = await createModelWithDataSource({ serverData });
    await mountSpreadsheet(model);
    createBasicChart(model, chartId);
    const sheetId = model.getters.getActiveSheetId();
    const chartFigureId = model.getters.getFigures(sheetId)[0].id;

    createCarousel(model, { items: [] }, "carouselId");
    addChartFigureToCarousel(model, "carouselId", chartFigureId);

    model.dispatch("UPDATE_ODOO_LINK_TO_CHART", {
        chartId,
        odooLink: { type: "odooMenu", odooMenuId: 2 },
    });
    model.updateMode("dashboard");
    await animationFrame();

    await contains(".o-carousel-header").click();
    expect.verifySteps([]);

    await contains(".o-carousel canvas").click();
    expect.verifySteps(["menuAction2"]);
});
