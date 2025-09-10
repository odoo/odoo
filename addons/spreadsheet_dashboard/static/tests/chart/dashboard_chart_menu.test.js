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
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";
import { mountSpreadsheet } from "@spreadsheet/../tests/helpers/ui";
import { defineSpreadsheetDashboardModels } from "@spreadsheet_dashboard/../tests/helpers/data";
import { contains, mockService, patchWithCleanup } from "@web/../tests/web_test_helpers";

defineSpreadsheetDashboardModels();

/**
 * @typedef {import("@spreadsheet/../tests/helpers/data").ServerData} ServerData
 */

const chartId = "uuid1";
let serverData = /** @type {ServerData} */ ({});

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
    serverData.models = {
        ...getBasicData(),
        "ir.ui.menu": {
            records: [{ id: 2, name: "test menu 2", action: "action2", group_ids: [10] }],
        },
        "res.group": { records: [{ id: 10, name: "test group" }] },
    };
});

test("Click on chart in dashboard mode redirect to the odoo menu", async function () {
    const doActionStep = "doAction";
    mockActionService(doActionStep);
    const { model } = await createModelWithDataSource({ serverData });
    const fixture = await mountSpreadsheet(model);

    createBasicChart(model, chartId);
    model.dispatch("LINK_ODOO_MENU_TO_CHART", {
        chartId,
        odooMenuId: 2,
    });
    const chartMenu = model.getters.getChartOdooMenu(chartId);
    expect(chartMenu.id).toBe(2, { message: "Odoo menu is linked to chart" });
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
            if (actionRequest === "menuAction2") {
                expect.step("chartMenuRedirect");
            } else if (
                actionRequest.type === "ir.actions.act_window" &&
                actionRequest.res_model === "partner"
            ) {
                expect.step("chartElementRedirect");
            }
        },
    });

    const { model } = await createModelWithDataSource({ serverData });
    const fixture = await mountSpreadsheet(model);
    const chartId = insertChartInSpreadsheet(model, "odoo_pie");
    model.dispatch("LINK_ODOO_MENU_TO_CHART", { chartId, odooMenuId: 2 });
    await animationFrame();
    model.updateMode("dashboard");
    await animationFrame();

    // Click pie element
    const chartCanvas = fixture.querySelector(".o-chart-container canvas");
    const canvasRect = chartCanvas.getBoundingClientRect();
    const canvasCenter = {
        x: canvasRect.left + canvasRect.width / 2,
        y: canvasRect.top + canvasRect.height / 2,
    };
    await click(".o-chart-container canvas", { position: canvasCenter, relative: true });
    await animationFrame();
    expect.verifySteps(["chartElementRedirect"]);

    // Click outside the pie element
    await click(".o-chart-container canvas", { position: "top-left" });
    await animationFrame();
    expect.verifySteps(["chartMenuRedirect"]);
});

test("Clicking on a scorecard or gauge redirects to the linked menu id", async function () {
    mockService("action", {
        doAction: async (actionRequest) => expect.step(actionRequest),
    });

    const { model } = await createModelWithDataSource({ serverData });
    await mountSpreadsheet(model);
    createScorecardChart(model, "scorecardId");
    createGaugeChart(model, "gaugeId");
    model.dispatch("LINK_ODOO_MENU_TO_CHART", { chartId: "scorecardId", odooMenuId: 2 });
    model.dispatch("LINK_ODOO_MENU_TO_CHART", { chartId: "gaugeId", odooMenuId: 2 });
    await animationFrame();

    model.updateMode("dashboard");
    await animationFrame();

    const chartCanvas = document.querySelectorAll(".o-figure canvas");

    await click(chartCanvas[0]);
    expect.verifySteps(["menuAction2"]);

    await click(chartCanvas[1]);
    expect.verifySteps(["menuAction2"]);
});

test.tags("desktop");
test("Middle-click on chart in dashboard mode open the odoo menu in a new tab", async function () {
    const { model } = await createModelWithDataSource({ serverData });
    await mountSpreadsheet(model);

    mockService("action", {
        doAction(_, options) {
            expect.step("doAction");
            expect(options).toEqual({
                newWindow: true,
            });
            return Promise.resolve(true);
        },
    });

    createBasicChart(model, chartId);
    model.dispatch("LINK_ODOO_MENU_TO_CHART", {
        chartId,
        odooMenuId: 2,
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
    model.dispatch("LINK_ODOO_MENU_TO_CHART", { chartId, odooMenuId: 2 });
    model.updateMode("dashboard");
    await animationFrame();

    await contains(".o-carousel-header").click();
    expect.verifySteps([]);

    await contains(".o-carousel canvas").click();
    expect.verifySteps(["menuAction2"]);
});
