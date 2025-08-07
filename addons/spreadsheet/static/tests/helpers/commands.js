/** @ts-check */

import * as spreadsheet from "@odoo/o-spreadsheet";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";
import { animationFrame } from "@odoo/hoot-mock";

const { toCartesian, toZone, lettersToNumber, deepCopy } = spreadsheet.helpers;

/**
 * @typedef {import("@spreadsheet").GlobalFilter} GlobalFilter
 * @typedef {import("@spreadsheet").CmdGlobalFilter} CmdGlobalFilter
 * @typedef {import("@spreadsheet").OdooSpreadsheetModel} OdooSpreadsheetModel
 * @typedef {import("@odoo/o-spreadsheet").UID} UID
 */

/**
 * Select a cell
 */
export function selectCell(model, xc, sheetId = model.getters.getActiveSheetId()) {
    const { col, row } = toCartesian(xc);
    if (sheetId !== model.getters.getActiveSheetId()) {
        model.dispatch("ACTIVATE_SHEET", { sheetIdTo: sheetId });
    }
    return model.selection.selectCell(col, row);
}

/**
 * Add a global filter. Does not wait for the data sources to be reloaded
 * @param {import("@spreadsheet").OdooSpreadsheetModel} model
 * @param {CmdGlobalFilter} filter
 */
export function addGlobalFilterWithoutReload(model, filter, fieldMatchings = {}) {
    return model.dispatch("ADD_GLOBAL_FILTER", { filter, ...fieldMatchings });
}

export function setGlobalFilterValueWithoutReload(model, payload) {
    return model.dispatch("SET_GLOBAL_FILTER_VALUE", payload);
}

/**
 * Add a global filter and ensure the data sources are completely reloaded
 * @param {import("@spreadsheet").OdooSpreadsheetModel} model
 * @param {CmdGlobalFilter} filter
 */
export async function addGlobalFilter(model, filter, fieldMatchings = {}) {
    const result = model.dispatch("ADD_GLOBAL_FILTER", { filter, ...fieldMatchings });
    // Wait for the fetch of DisplayNames
    await animationFrame();
    await waitForDataLoaded(model);
    return result;
}

/**
 * Remove a global filter and ensure the data sources are completely reloaded
 */
export async function removeGlobalFilter(model, id) {
    const result = model.dispatch("REMOVE_GLOBAL_FILTER", { id });
    // Wait for the fetch of DisplayNames
    await animationFrame();
    await waitForDataLoaded(model);
    return result;
}

/**
 * Edit a global filter and ensure the data sources are completely reloaded
 * @param {Model} model
 * @param {CmdGlobalFilter} filter
 */
export async function editGlobalFilter(model, filter) {
    const result = model.dispatch("EDIT_GLOBAL_FILTER", { filter });
    // Wait for the fetch of DisplayNames
    await animationFrame();
    await waitForDataLoaded(model);
    return result;
}

/**
 * Set the value of a global filter and ensure the data sources are completely
 * reloaded
 */
export async function setGlobalFilterValue(model, payload) {
    const result = model.dispatch("SET_GLOBAL_FILTER_VALUE", payload);
    // Wait for the fetch of DisplayNames
    await animationFrame();
    await waitForDataLoaded(model);
    return result;
}

export function moveGlobalFilter(model, id, delta) {
    return model.dispatch("MOVE_GLOBAL_FILTER", { id, delta });
}

/**
 * Set the selection
 */
export function setSelection(model, xc) {
    const zone = toZone(xc);
    model.selection.selectZone({ cell: { col: zone.left, row: zone.top }, zone });
}

/**
 * Autofill from a zone to a cell
 */
export function autofill(model, from, to) {
    setSelection(model, from);
    model.dispatch("AUTOFILL_SELECT", toCartesian(to));
    model.dispatch("AUTOFILL");
}

/**
 * Set the content of a cell
 */
export function setCellContent(model, xc, content, sheetId = model.getters.getActiveSheetId()) {
    model.dispatch("UPDATE_CELL", { ...toCartesian(xc), sheetId, content });
}

/**
 * Set the format of a cell
 */
export function setCellFormat(model, xc, format, sheetId = model.getters.getActiveSheetId()) {
    model.dispatch("UPDATE_CELL", { ...toCartesian(xc), sheetId, format });
}

/**
 * Set the style of a cell
 */
export function setCellStyle(model, xc, style, sheetId = model.getters.getActiveSheetId()) {
    model.dispatch("UPDATE_CELL", { ...toCartesian(xc), sheetId, style });
}

/**
 * Add columns
 * @param {OdooSpreadsheetModel} model
 * @param {"before"|"after"} position
 * @param {string} column
 * @param {number} quantity
 * @param {UID} sheetId
 */
export function addColumns(
    model,
    position,
    column,
    quantity,
    sheetId = model.getters.getActiveSheetId()
) {
    return model.dispatch("ADD_COLUMNS_ROWS", {
        sheetId,
        dimension: "COL",
        position,
        base: lettersToNumber(column),
        quantity,
    });
}

/**
 * Delete columns
 * @param {OdooSpreadsheetModel} model
 * @param {string[]} columns
 * @param {UID} sheetId
 */
export function deleteColumns(model, columns, sheetId = model.getters.getActiveSheetId()) {
    return model.dispatch("REMOVE_COLUMNS_ROWS", {
        sheetId,
        dimension: "COL",
        elements: columns.map(lettersToNumber),
    });
}

/** Create a test chart in the active sheet*/
export function createBasicChart(
    model,
    chartId,
    definition,
    sheetId = model.getters.getActiveSheetId(),
    figureId = model.uuidGenerator.smallUuid()
) {
    model.dispatch("CREATE_CHART", {
        chartId,
        figureId,
        col: 0,
        row: 0,
        offset: {
            x: 0,
            y: 0,
        },
        sheetId: sheetId,
        definition: {
            title: { text: "test" },
            dataSets: [{ dataRange: "A1" }],
            type: "bar",
            background: "#fff",
            verticalAxisPosition: "left",
            legendPosition: "top",
            stackedBar: false,
            ...definition,
        },
    });
}

/** Create a test scorecard chart in the active sheet*/
export function createScorecardChart(
    model,
    chartId,
    sheetId = model.getters.getActiveSheetId(),
    figureId = model.uuidGenerator.smallUuid()
) {
    model.dispatch("CREATE_CHART", {
        figureId,
        chartId,
        col: 0,
        row: 0,
        offset: { x: 0, y: 0 },
        sheetId: sheetId,
        definition: {
            title: { text: "test" },
            keyValue: "A1",
            type: "scorecard",
            background: "#fff",
            baselineColorDown: "#DC6965",
            baselineColorUp: "#00A04A",
            baselineMode: "absolute",
        },
    });
}

/** Create a test scorecard chart in the active sheet*/
export function createGaugeChart(
    model,
    chartId,
    sheetId = model.getters.getActiveSheetId(),
    figureId = model.uuidGenerator.smallUuid()
) {
    model.dispatch("CREATE_CHART", {
        figureId,
        chartId,
        col: 0,
        row: 0,
        offset: { x: 0, y: 0 },
        sheetId: sheetId,
        definition: {
            title: { text: "test" },
            type: "gauge",
            background: "#fff",
            dataRange: "A1",
            sectionRule: {
                rangeMin: "0",
                rangeMax: "100",
                colors: {
                    lowerColor: "#112233",
                    middleColor: "#445566",
                    upperColor: "#778899",
                },
                lowerInflectionPoint: {
                    type: "number",
                    value: "25",
                },
                upperInflectionPoint: {
                    type: "number",
                    value: "85",
                },
            },
        },
    });
}

export function updateChart(model, chartId, partialDefinition) {
    const definition = model.getters.getChartDefinition(chartId);
    return model.dispatch("UPDATE_CHART", {
        definition: { ...definition, ...partialDefinition },
        chartId,
        figureId: model.getters.getFigureIdFromChartId(chartId),
        sheetId: model.getters.getActiveSheetId(),
    });
}

export function undo(model) {
    model.dispatch("REQUEST_UNDO");
}

export function redo(model) {
    model.dispatch("REQUEST_REDO");
}

export function updatePivot(model, pivotId, pivotData) {
    const pivot = {
        ...model.getters.getPivotCoreDefinition(pivotId),
        ...pivotData,
    };
    return model.dispatch("UPDATE_PIVOT", { pivotId, pivot });
}

/**
 * Copy a zone
 */
export function copy(model, xc) {
    setSelection(model, xc);
    return model.dispatch("COPY");
}

/**
 * Cut a zone
 */
export function cut(model, xc) {
    setSelection(model, xc);
    return model.dispatch("CUT");
}

/**
 * Paste on a zone
 */
export function paste(model, range, pasteOption) {
    return model.dispatch("PASTE", { target: [toZone(range)], pasteOption });
}

export function updatePivotMeasureDisplay(model, pivotId, measureId, display) {
    const measures = deepCopy(model.getters.getPivotCoreDefinition(pivotId)).measures;
    const measure = measures.find((m) => m.id === measureId);
    measure.display = display;
    updatePivot(model, pivotId, { measures });
}

export function createSheet(model, data = {}) {
    const sheetId = data.sheetId || model.uuidGenerator.smallUuid();
    return model.dispatch("CREATE_SHEET", {
        position: data.position !== undefined ? data.position : 1,
        sheetId,
        cols: data.cols,
        rows: data.rows,
        name: data.name,
    });
}

export function createCarousel(model, data = { items: [] }, carouselId, sheetId, figureData = {}) {
    return model.dispatch("CREATE_CAROUSEL", {
        figureId: carouselId || model.uuidGenerator.smallUuid(),
        sheetId: sheetId || model.getters.getActiveSheetId(),
        col: 0,
        row: 0,
        definition: data,
        size: { width: 500, height: 300 },
        offset: { x: 0, y: 0 },
        ...figureData,
    });
}
