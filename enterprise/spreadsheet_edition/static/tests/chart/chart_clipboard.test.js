import { describe, expect, test } from "@odoo/hoot";
import { Model, helpers } from "@odoo/o-spreadsheet";
import {
    createSpreadsheetWithChart,
    insertChartInSpreadsheet,
} from "@spreadsheet/../tests/helpers/chart";
import { addGlobalFilter, createBasicChart } from "@spreadsheet/../tests/helpers/commands";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { makeSpreadsheetMockEnv } from "@spreadsheet/../tests/helpers/model";

describe.current.tags("headless");
defineSpreadsheetModels();

const { toZone } = helpers;
const chartId = "uuid1";

const serverData = {
    menus: {
        root: {
            id: "root",
            children: [1],
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
    },
};

test("link is kept when copying chart", async () => {
    const env = await makeSpreadsheetMockEnv({ serverData });
    const model = new Model({}, { custom: { env } });
    createBasicChart(model, chartId);
    model.dispatch("LINK_ODOO_MENU_TO_CHART", {
        chartId,
        odooMenuId: 1,
    });
    expect(model.getters.getChartOdooMenu(chartId).id).toBe(1);
    model.dispatch("UPDATE_CHART", {
        sheetId: model.getters.getActiveSheetId(),
        id: chartId,
        definition: {
            ...model.getters.getChartDefinition(chartId),
            type: "line",
        },
    });
    expect(model.getters.getChartOdooMenu(chartId).id).toBe(1);
    const sheetId = model.getters.getActiveSheetId();
    model.dispatch("SELECT_FIGURE", { id: chartId });
    model.dispatch("COPY");
    model.dispatch("PASTE", { target: [toZone("A1")] });
    const chartIds = model.getters.getChartIds(sheetId);
    expect(chartIds.length).toBe(2);
    for (const _chartId of chartIds) {
        expect(model.getters.getChartOdooMenu(_chartId).id).toBe(1);
    }
});

test("copy/paste Odoo chart field matching", async () => {
    const { model } = await createSpreadsheetWithChart({ type: "odoo_pie" });
    insertChartInSpreadsheet(model, "odoo_bar");
    const sheetId = model.getters.getActiveSheetId();
    const [chartId1, chartId2] = model.getters.getChartIds(sheetId);
    const fieldMatching = {
        chart: {
            [chartId1]: { type: "many2one", chain: "partner_id.company_id" },
            [chartId2]: { type: "many2one", chain: "user_id.company_id" },
        },
    };
    const filterId = "44";
    await addGlobalFilter(
        model,
        {
            id: filterId,
            type: "relation",
            modelName: "res.company",
            label: "Relation Filter",
        },
        fieldMatching
    );
    model.dispatch("SELECT_FIGURE", { id: chartId2 });
    model.dispatch("COPY");
    model.dispatch("PASTE", { target: [toZone("A1")] });
    const chartIds = model.getters.getChartIds(sheetId);
    expect(model.getters.getOdooChartFieldMatching(chartId1, filterId).chain).toBe(
        "partner_id.company_id"
    );
    expect(model.getters.getOdooChartFieldMatching(chartId2, filterId).chain).toBe(
        "user_id.company_id"
    );
    expect(model.getters.getOdooChartFieldMatching(chartIds[2], filterId).chain).toBe(
        "user_id.company_id"
    );
});

test("cut/paste Odoo chart field matching", async () => {
    const { model } = await createSpreadsheetWithChart({ type: "odoo_pie" });
    insertChartInSpreadsheet(model, "odoo_bar");
    const sheetId = model.getters.getActiveSheetId();
    const [chartId1, chartId2] = model.getters.getChartIds(sheetId);
    const fieldMatching = {
        chart: {
            [chartId1]: { type: "many2one", chain: "partner_id.company_id" },
            [chartId2]: { type: "many2one", chain: "user_id.company_id" },
        },
    };
    const filterId = "44";
    await addGlobalFilter(
        model,
        {
            id: filterId,
            type: "relation",
            modelName: "res.company",
            label: "Relation Filter",
        },
        fieldMatching
    );
    model.dispatch("SELECT_FIGURE", { id: chartId2 });
    model.dispatch("CUT");
    model.dispatch("PASTE", { target: [toZone("A1")] });
    const chartIds = model.getters.getChartIds(sheetId);
    expect(model.getters.getOdooChartFieldMatching(chartId1, filterId).chain).toBe(
        "partner_id.company_id"
    );
    expect(() => model.getters.getChartFieldMatch(chartId2)).toThrow(undefined);
    expect(model.getters.getOdooChartFieldMatching(chartIds[1], filterId).chain).toBe(
        "user_id.company_id"
    );
});
