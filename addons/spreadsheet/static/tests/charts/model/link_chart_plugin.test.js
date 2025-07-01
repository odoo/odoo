import { describe, expect, test } from "@odoo/hoot";
import { createSpreadsheetWithChart } from "@spreadsheet/../tests/helpers/chart";
import { createBasicChart } from "@spreadsheet/../tests/helpers/commands";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { makeMockEnv } from "@web/../tests/web_test_helpers";

import { Model } from "@odoo/o-spreadsheet";

const chartId = "uuid1";

describe.current.tags("headless");

defineSpreadsheetModels();

test("Links between charts and ir.menus are correctly imported/exported", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { env } });
    createBasicChart(model, chartId);
    model.dispatch("LINK_ODOO_MENU_TO_CHART", {
        chartId,
        odooMenuId: 1,
    });
    const exportedData = model.exportData();
    expect(exportedData.chartOdooMenusReferences[chartId]).toBe(1, {
        message: "Link to odoo menu is exported",
    });
    const importedModel = new Model(exportedData, { custom: { env } });
    const chartMenu = importedModel.getters.getChartOdooMenu(chartId);
    expect(chartMenu.id).toBe(1, { message: "Link to odoo menu is imported" });
});

test("Can undo-redo a LINK_ODOO_MENU_TO_CHART", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { env } });
    createBasicChart(model, chartId);
    model.dispatch("LINK_ODOO_MENU_TO_CHART", {
        chartId,
        odooMenuId: 1,
    });
    expect(model.getters.getChartOdooMenu(chartId).id).toBe(1);
    model.dispatch("REQUEST_UNDO");
    expect(model.getters.getChartOdooMenu(chartId)).toBe(undefined);
    model.dispatch("REQUEST_REDO");
    expect(model.getters.getChartOdooMenu(chartId).id).toBe(1);
});

test("link is removed when figure is deleted", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { env } });
    createBasicChart(model, chartId);
    model.dispatch("LINK_ODOO_MENU_TO_CHART", {
        chartId,
        odooMenuId: 1,
    });
    expect(model.getters.getChartOdooMenu(chartId).id).toBe(1);
    model.dispatch("DELETE_FIGURE", {
        sheetId: model.getters.getActiveSheetId(),
        id: chartId,
    });
    expect(model.getters.getChartOdooMenu(chartId)).toBe(undefined);
});

test("Links of Odoo charts are duplicated when duplicating a sheet", async function () {
    const { model } = await createSpreadsheetWithChart({ type: "odoo_pie" });
    const sheetId = model.getters.getActiveSheetId();
    const secondSheetId = "mySecondSheetId";
    const chartId = model.getters.getChartIds(sheetId)[0];
    model.dispatch("DUPLICATE_SHEET", { sheetId, sheetIdTo: secondSheetId });
    const newChartId = model.getters.getChartIds(secondSheetId)[0];
    expect(model.getters.getChartOdooMenu(newChartId)).toEqual(
        model.getters.getChartOdooMenu(chartId)
    );
});

test("Links of standard charts are duplicated when duplicating a sheet", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { env } });
    const sheetId = model.getters.getActiveSheetId();
    const secondSheetId = "mySecondSheetId";
    createBasicChart(model, chartId);
    model.dispatch("LINK_ODOO_MENU_TO_CHART", {
        chartId,
        odooMenuId: 1,
    });
    model.dispatch("DUPLICATE_SHEET", { sheetId, sheetIdTo: secondSheetId });
    const newChartId = model.getters.getChartIds(secondSheetId)[0];
    expect(model.getters.getChartOdooMenu(newChartId)).toEqual(
        model.getters.getChartOdooMenu(chartId)
    );
});
