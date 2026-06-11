import { animationFrame } from "@odoo/hoot-mock";
import { expect, test, beforeEach } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";

import {
    defineSpreadsheetActions,
    defineSpreadsheetModels,
    getBasicData,
} from "@spreadsheet/../tests/helpers/data";
import { mountSpreadsheet } from "@spreadsheet/../tests/helpers/ui";
import { createSpreadsheetWithList } from "@spreadsheet/../tests/helpers/list";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";
import { mockService, serverState } from "@web/../tests/web_test_helpers";

defineSpreadsheetModels();
defineSpreadsheetActions();

const chartId = "uuid1";
let serverData;

/**
 * Create a scorecard chart with an empty title so `config.title` is undefined,
 * ensuring that clicks in the key region don't accidentally land in the title region.
 */
function createScorecardChart(model, definition = {}) {
    model.dispatch("CREATE_CHART", {
        figureId: "scorecardFig",
        chartId,
        col: 0,
        row: 0,
        offset: { x: 0, y: 0 },
        sheetId: model.getters.getActiveSheetId(),
        definition: {
            title: { text: "Title" },
            keyValue: "A1",
            type: "scorecard",
            background: "#fff",
            baselineColorDown: "#DC6965",
            baselineColorUp: "#00A04A",
            baselineMode: "absolute",
            ...definition,
        },
    });
}

async function clickCanvas(fixture, region) {
    const canvas = fixture.querySelector("canvas");
    const { height } = canvas.getBoundingClientRect();
    // KEY section sits at ~45% of canvas height, BASELINE at ~90%.
    const y = region === "baseline" ? height * 0.9 : height * 0.45;
    await click(canvas, { position: { x: 0, y }, relative: true });
}

beforeEach(() => {
    serverData = {
        menus: {
            1: {
                id: 1,
                name: "test menu",
                xmlid: "spreadsheet.test.menu",
                appID: 1,
                actionID: "menuAction",
            },
        },
        actions: {
            menuAction: {
                id: 99,
                xml_id: "menuAction",
                name: "menuAction",
                res_model: "ir.ui.menu",
                type: "ir.actions.act_window",
                views: [[false, "list"]],
            },
        },
        models: {
            ...getBasicData(),
            "ir.ui.menu": {
                records: [{ id: 1, name: "test menu", action: "menuAction", group_ids: [10] }],
            },
            "res.group": { records: [{ id: 10, name: "test group" }] },
            "res.users": {
                records: [
                    { id: 1, active: true, partner_id: serverState.partnerId, name: "Raoul" },
                ],
            },
            "ir.actions": { records: [{ id: 1 }] },
        },
    };
    serverState.userId = 1;
});

test("clicking scorecard outside dashboard mode does nothing", async function () {
    mockService("action", {
        doAction: () => expect.step("doAction"),
    });
    const { model } = await createModelWithDataSource({ serverData });
    const fixture = await mountSpreadsheet(model);
    createScorecardChart(model);
    model.dispatch("UPDATE_ODOO_LINK_TO_CHART", {
        chartId,
        odooLink: { type: "odooMenu", odooMenuId: 1 },
    });
    await animationFrame();
    await clickCanvas(fixture, "key");
    expect.verifySteps([]);
});

test("clicking scorecard in dashboard mode navigates to odoo link", async function () {
    mockService("action", {
        doAction: (action) => {
            if (action === "menuAction" || action.xml_id === "menuAction") {
                expect.step("navigate");
            }
        },
    });
    const { model } = await createModelWithDataSource({ serverData });
    const fixture = await mountSpreadsheet(model);
    createScorecardChart(model);
    model.dispatch("UPDATE_ODOO_LINK_TO_CHART", {
        chartId,
        odooLink: { type: "odooMenu", odooMenuId: 1 },
    });
    model.updateMode("dashboard");
    await animationFrame();
    await clickCanvas(fixture, "key");
    expect.verifySteps(["navigate"]);
});

test("clicking key area opens seeRecord when key cell has a list record", async function () {
    mockService("action", {
        async doAction(action) {
            if (action?.views?.[0]?.[1] === "form") {
                expect.step(`seeRecord:${action.res_id}`);
            }
        },
    });
    const { model } = await createSpreadsheetWithList();
    const fixture = await mountSpreadsheet(model);
    createScorecardChart(model, { keyValue: "A2" });
    model.updateMode("dashboard");
    await animationFrame();
    await clickCanvas(fixture, "key");
    expect.verifySteps(["seeRecord:1"]);
});

test("clicking baseline area opens seeRecord when baseline cell has a list record", async function () {
    mockService("action", {
        async doAction(action) {
            if (action?.views?.[0]?.[1] === "form") {
                expect.step(`seeRecord:${action.res_id}`);
            }
        },
    });
    const { model } = await createSpreadsheetWithList();
    const fixture = await mountSpreadsheet(model);
    createScorecardChart(model, { keyValue: "A2", baseline: "A2" });
    model.updateMode("dashboard");
    await animationFrame();
    await clickCanvas(fixture, "baseline");
    expect.verifySteps(["seeRecord:1"]);
});
