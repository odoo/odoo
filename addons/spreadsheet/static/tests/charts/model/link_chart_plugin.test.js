import { describe, expect, test } from "@odoo/hoot";
import { insertChartInSpreadsheet } from "@spreadsheet/../tests/helpers/chart";
import { createBasicChart } from "@spreadsheet/../tests/helpers/commands";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/helpers/pivot";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";
import { createSpreadsheetWithList } from "../../helpers/list";
import { CommandResult } from "@spreadsheet/o_spreadsheet/cancelled_reason";

const chartId = "uuid1";

describe.current.tags("headless");

defineSpreadsheetModels();

test("Links between charts and datasources are correctly imported/exported", async function () {
    const { model, pivotId } = await createSpreadsheetWithPivot();
    createBasicChart(model, chartId);
    model.dispatch("LINK_ODOO_DATASOURCE_TO_CHART", {
        chartId,
        odooDataSource: { dataSourceId: pivotId, type: "pivot" },
    });
    const exportedData = model.exportData();
    expect(exportedData.chartOdooDataSourcesReference[chartId]).toEqual(
        { dataSourceId: pivotId, type: "pivot" },
        {
            message: "Link to odoo menu is exported",
        }
    );
    const { model: importedModel } = await createModelWithDataSource({
        spreadsheetData: exportedData,
    });
    const dataSourceLink = importedModel.getters.getChartLinkedDataSource(chartId);
    expect(dataSourceLink).toEqual(
        { dataSourceId: pivotId, type: "pivot" },
        { message: "Link to odoo menu is imported" }
    );
});

test("Can undo-redo a LINK_ODOO_DATASOURCE_TO_CHART", async function () {
    const { model, pivotId } = await createSpreadsheetWithPivot();
    createBasicChart(model, chartId);
    model.dispatch("LINK_ODOO_DATASOURCE_TO_CHART", {
        chartId,
        odooDataSource: { dataSourceId: pivotId, type: "pivot" },
    });
    expect(model.getters.getChartLinkedDataSource(chartId)).toEqual({
        dataSourceId: pivotId,
        type: "pivot",
    });
    model.dispatch("REQUEST_UNDO");
    expect(model.getters.getChartLinkedDataSource(chartId)).toBe(undefined);
    model.dispatch("REQUEST_REDO");
    expect(model.getters.getChartLinkedDataSource(chartId)).toEqual({
        dataSourceId: pivotId,
        type: "pivot",
    });
});

test("link is removed when figure is deleted", async function () {
    const { model, pivotId } = await createSpreadsheetWithPivot();
    createBasicChart(model, chartId);
    model.dispatch("LINK_ODOO_DATASOURCE_TO_CHART", {
        chartId,
        odooDataSource: { dataSourceId: pivotId, type: "pivot" },
    });
    expect(model.getters.getChartLinkedDataSource(chartId)).toEqual({
        dataSourceId: pivotId,
        type: "pivot",
    });
    model.dispatch("DELETE_FIGURE", {
        sheetId: model.getters.getActiveSheetId(),
        figureId: model.getters.getFigureIdFromChartId(chartId),
    });
    expect(model.getters.getChartLinkedDataSource(chartId)).toBe(undefined);
});

test("Links of Odoo charts are duplicated when duplicating a sheet", async function () {
    const { model, pivotId } = await createSpreadsheetWithPivot();
    insertChartInSpreadsheet(model, "odoo_pie");
    const sheetId = model.getters.getActiveSheetId();
    const secondSheetId = "mySecondSheetId";
    const chartId = model.getters.getChartIds(sheetId)[0];
    model.dispatch("LINK_ODOO_DATASOURCE_TO_CHART", {
        chartId,
        odooDataSource: { dataSourceId: pivotId, type: "pivot" },
    });
    model.dispatch("DUPLICATE_SHEET", { sheetId, sheetIdTo: secondSheetId });
    const newChartId = model.getters.getChartIds(secondSheetId)[0];
    expect(model.getters.getChartLinkedDataSource(newChartId)).toEqual(
        model.getters.getChartLinkedDataSource(chartId)
    );
});

test("Links of standard charts are duplicated when duplicating a sheet", async function () {
    const { model, pivotId } = await createSpreadsheetWithPivot();
    const sheetId = model.getters.getActiveSheetId();
    const secondSheetId = "mySecondSheetId";
    createBasicChart(model, chartId);
    model.dispatch("LINK_ODOO_DATASOURCE_TO_CHART", {
        chartId,
        odooDataSource: { dataSourceId: pivotId, type: "pivot" },
    });
    model.dispatch("DUPLICATE_SHEET", { sheetId, sheetIdTo: secondSheetId });
    const newChartId = model.getters.getChartIds(secondSheetId)[0];
    expect(model.getters.getChartLinkedDataSource(newChartId)).toEqual(
        model.getters.getChartLinkedDataSource(chartId)
    );
});

test("Datasource link is removed when a pivot is deleted", async function () {
    const { model, pivotId } = await createSpreadsheetWithPivot();
    createBasicChart(model, chartId);
    model.dispatch("LINK_ODOO_DATASOURCE_TO_CHART", {
        chartId,
        odooDataSource: { dataSourceId: pivotId, type: "pivot" },
    });
    expect(model.getters.getChartLinkedDataSource(chartId)).toEqual({
        dataSourceId: pivotId,
        type: "pivot",
    });
    model.dispatch("REMOVE_PIVOT", { pivotId });
    expect(model.getters.getChartLinkedDataSource(chartId)).toBe(undefined);
    console.log("exportData", model.exportData());
    expect(model.exportData().chartOdooDataSourcesReference).toBeEmpty();
});

test("Datasource link is removed when a list is deleted", async function () {
    const { model } = await createSpreadsheetWithList();
    const listId = model.getters.getListIds()[0];
    createBasicChart(model, chartId);
    model.dispatch("LINK_ODOO_DATASOURCE_TO_CHART", {
        chartId,
        odooDataSource: { dataSourceId: listId, type: "list" },
    });
    expect(model.getters.getChartLinkedDataSource(chartId)).toEqual({
        dataSourceId: listId,
        type: "list",
    });
    model.dispatch("REMOVE_ODOO_LIST", { listId });
    expect(model.getters.getChartLinkedDataSource(chartId)).toBe(undefined);
    console.log("exportData", model.exportData());
    expect(model.exportData().chartOdooDataSourcesReference).toBeEmpty();
});

test("Datasource link is removed when an odoo chart is deleted", async function () {
    const { model } = await createModelWithDataSource();
    const odooChartId = insertChartInSpreadsheet(model, "odoo_line");
    createBasicChart(model, chartId);
    model.dispatch("LINK_ODOO_DATASOURCE_TO_CHART", {
        chartId,
        odooDataSource: { dataSourceId: odooChartId, type: "chart" },
    });
    expect(model.getters.getChartLinkedDataSource(chartId)).toEqual({
        dataSourceId: odooChartId,
        type: "chart",
    });
    model.dispatch("DELETE_FIGURE", {
        figureId: model.getters.getFigureIdFromChartId(odooChartId),
        sheetId: model.getters.getActiveSheetId(),
    });
    expect(model.getters.getChartLinkedDataSource(chartId)).toBe(undefined);
    console.log("exportData", model.exportData());
    expect(model.exportData().chartOdooDataSourcesReference).toBeEmpty();
});

test("cannot link against a non-existing datasource", async function () {
    const { model, pivotId } = await createSpreadsheetWithPivot();
    createBasicChart(model, chartId);
    const result1 = model.dispatch("LINK_ODOO_DATASOURCE_TO_CHART", {
        chartId,
        odooDataSource: { dataSourceId: pivotId, type: "notAType" },
    });
    expect(result1.reasons).toEqual([CommandResult.InvalidDataSourceType]);
    const result2 = model.dispatch("LINK_ODOO_DATASOURCE_TO_CHART", {
        chartId,
        odooDataSource: { dataSourceId: "coucou", type: "pivot" },
    });
    expect(result2.reasons).toEqual([CommandResult.InvalidDataSourceId]);
});
