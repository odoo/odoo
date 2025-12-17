import { describe, expect, test } from "@odoo/hoot";
import { insertChartInSpreadsheet } from "@spreadsheet/../tests/helpers/chart";
import { createBasicChart } from "@spreadsheet/../tests/helpers/commands";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/helpers/pivot";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";
import { createSpreadsheetWithList } from "../../helpers/list";
import { CommandResult } from "@spreadsheet/o_spreadsheet/cancelled_reason";
import { makeMockEnv } from "@web/../tests/web_test_helpers";

import { Model } from "@odoo/o-spreadsheet";

const chartId = "uuid1";

describe.current.tags("headless");

defineSpreadsheetModels();

test("Links between charts and ir.menus are correctly imported/exported", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { env } });
    createBasicChart(model, chartId);
    model.dispatch("UPDATE_ODOO_LINK_TO_CHART", {
        chartId,
        odooLink: { type: "odooMenu", odooMenuId: 1 },
    });
    const exportedData = model.exportData();
    expect(exportedData.odooLinkReferences[chartId]).toEqual(
        { type: "odooMenu", odooMenuId: 1 },
        { message: "Link to odoo menu is exported" }
    );
    const importedModel = new Model(exportedData, { custom: { env } });
    const chartMenu = importedModel.getters.getChartOdooLink(chartId);
    expect(chartMenu).toEqual(
        { type: "odooMenu", odooMenuId: 1 },
        { message: "Link to odoo menu is imported" }
    );
});

test("Links between charts and datasources are correctly imported/exported", async function () {
    const { model, pivotId } = await createSpreadsheetWithPivot();
    createBasicChart(model, chartId);
    model.dispatch("UPDATE_ODOO_LINK_TO_CHART", {
        chartId,
        odooLink: { type: "dataSource", dataSourceType: "pivot", dataSourceCoreId: pivotId },
    });
    const exportedData = model.exportData();
    expect(exportedData.odooLinkReferences[chartId]).toEqual(
        { type: "dataSource", dataSourceType: "pivot", dataSourceCoreId: pivotId },
        {
            message: "Link to datasource is exported",
        }
    );
    const { model: importedModel } = await createModelWithDataSource({
        spreadsheetData: exportedData,
    });
    const dataSourceLink = importedModel.getters.getChartOdooLink(chartId);
    expect(dataSourceLink).toEqual(
        { type: "dataSource", dataSourceType: "pivot", dataSourceCoreId: pivotId },
        { message: "Link to odoo datasource is imported" }
    );
});

test("Can undo-redo a UPDATE_ODOO_LINK_TO_CHART", async function () {
    const { model, pivotId } = await createSpreadsheetWithPivot();
    createBasicChart(model, chartId);
    model.dispatch("UPDATE_ODOO_LINK_TO_CHART", {
        chartId,
        odooLink: { type: "dataSource", dataSourceType: "pivot", dataSourceCoreId: pivotId },
    });
    expect(model.getters.getChartOdooLink(chartId)).toEqual({
        type: "dataSource",
        dataSourceCoreId: pivotId,
        dataSourceType: "pivot",
    });
    model.dispatch("REQUEST_UNDO");
    expect(model.getters.getChartOdooLink(chartId)).toBe(undefined);
    model.dispatch("REQUEST_REDO");
    expect(model.getters.getChartOdooLink(chartId)).toEqual({
        type: "dataSource",
        dataSourceCoreId: pivotId,
        dataSourceType: "pivot",
    });
});

test("link is removed when figure is deleted", async function () {
    const { model, pivotId } = await createSpreadsheetWithPivot();
    createBasicChart(model, chartId);
    model.dispatch("UPDATE_ODOO_LINK_TO_CHART", {
        chartId,
        odooLink: { type: "dataSource", dataSourceType: "pivot", dataSourceCoreId: pivotId },
    });
    expect(model.getters.getChartOdooLink(chartId)).toEqual({
        dataSourceCoreId: pivotId,
        type: "dataSource",
        dataSourceType: "pivot",
    });
    model.dispatch("DELETE_FIGURE", {
        sheetId: model.getters.getActiveSheetId(),
        figureId: model.getters.getFigureIdFromChartId(chartId),
    });
    expect(model.getters.getChartOdooLink(chartId)).toBe(undefined);
});

test("Links of Odoo charts are duplicated when duplicating a sheet", async function () {
    const { model, pivotId } = await createSpreadsheetWithPivot();
    insertChartInSpreadsheet(model, "odoo_pie");
    const sheetId = model.getters.getActiveSheetId();
    const secondSheetId = "mySecondSheetId";
    const chartId = model.getters.getChartIds(sheetId)[0];
    model.dispatch("UPDATE_ODOO_LINK_TO_CHART", {
        chartId,
        odooLink: { type: "dataSource", dataSourceType: "pivot", dataSourceCoreId: pivotId },
    });
    model.dispatch("DUPLICATE_SHEET", {
        sheetId,
        sheetIdTo: secondSheetId,
        sheetNameTo: "Next Name",
    });
    const newChartId = model.getters.getChartIds(secondSheetId)[0];
    expect(model.getters.getChartOdooLink(newChartId)).toEqual(
        model.getters.getChartOdooLink(chartId)
    );
});

test("Links of standard charts are duplicated when duplicating a sheet", async function () {
    const { model, pivotId } = await createSpreadsheetWithPivot();
    const sheetId = model.getters.getActiveSheetId();
    const secondSheetId = "mySecondSheetId";
    createBasicChart(model, chartId);
    model.dispatch("UPDATE_ODOO_LINK_TO_CHART", {
        chartId,
        odooLink: { type: "dataSource", dataSourceType: "pivot", dataSourceCoreId: pivotId },
    });
    model.dispatch("DUPLICATE_SHEET", {
        sheetId,
        sheetIdTo: secondSheetId,
        sheetNameTo: "Next Name",
    });
    const newChartId = model.getters.getChartIds(secondSheetId)[0];
    expect(model.getters.getChartOdooLink(newChartId)).toEqual(
        model.getters.getChartOdooLink(chartId)
    );
});

test("Datasource link is removed when a pivot is deleted", async function () {
    const { model, pivotId } = await createSpreadsheetWithPivot();
    createBasicChart(model, chartId);
    model.dispatch("UPDATE_ODOO_LINK_TO_CHART", {
        chartId,
        odooLink: { type: "dataSource", dataSourceType: "pivot", dataSourceCoreId: pivotId },
    });
    expect(model.getters.getChartOdooLink(chartId)).toEqual({
        type: "dataSource",
        dataSourceType: "pivot",
        dataSourceCoreId: pivotId,
    });
    model.dispatch("REMOVE_PIVOT", { pivotId });
    expect(model.getters.getChartOdooLink(chartId)).toBe(undefined);
    console.log("exportData", model.exportData());
    expect(model.exportData().odooLinkReferences).toBeEmpty();
});

test("Datasource link is removed when a list is deleted", async function () {
    const { model } = await createSpreadsheetWithList();
    const listId = model.getters.getListIds()[0];
    createBasicChart(model, chartId);
    model.dispatch("UPDATE_ODOO_LINK_TO_CHART", {
        chartId,
        odooLink: { dataSourceCoreId: listId, type: "dataSource", dataSourceType: "list" },
    });
    expect(model.getters.getChartOdooLink(chartId)).toEqual({
        dataSourceCoreId: listId,
        type: "dataSource",
        dataSourceType: "list",
    });
    model.dispatch("REMOVE_ODOO_LIST", { listId });
    expect(model.getters.getChartOdooLink(chartId)).toBe(undefined);
    console.log("exportData", model.exportData());
    expect(model.exportData().odooLinkReferences).toBeEmpty();
});

test("Datasource link is removed when an odoo chart is deleted", async function () {
    const { model } = await createModelWithDataSource();
    const odooChartId = insertChartInSpreadsheet(model, "odoo_line");
    createBasicChart(model, chartId);
    model.dispatch("UPDATE_ODOO_LINK_TO_CHART", {
        chartId,
        odooLink: { dataSourceCoreId: odooChartId, type: "dataSource", dataSourceType: "chart" },
    });
    expect(model.getters.getChartOdooLink(chartId)).toEqual({
        dataSourceCoreId: odooChartId,
        type: "dataSource",
        dataSourceType: "chart",
    });
    model.dispatch("DELETE_FIGURE", {
        figureId: model.getters.getFigureIdFromChartId(odooChartId),
        sheetId: model.getters.getActiveSheetId(),
    });
    expect(model.getters.getChartOdooLink(chartId)).toBe(undefined);
    console.log("exportData", model.exportData());
    expect(model.exportData().odooLinkReferences).toBeEmpty();
});

test("cannot link against a non-existing datasource", async function () {
    const { model, pivotId } = await createSpreadsheetWithPivot();
    createBasicChart(model, chartId);
    const result1 = model.dispatch("UPDATE_ODOO_LINK_TO_CHART", {
        chartId,
        odooLink: { dataSourceCoreId: pivotId, type: "dataSource", dataSourceType: "shityType" },
    });
    expect(result1.reasons).toEqual([CommandResult.InvalidDataSourceType]);
    const result2 = model.dispatch("UPDATE_ODOO_LINK_TO_CHART", {
        chartId,
        odooLink: { dataSourceCoreId: "coucou", type: "dataSource", dataSourceType: "pivot" },
    });
    expect(result2.reasons).toEqual([CommandResult.InvalidDataSourceId]);
});
