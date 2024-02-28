/** @odoo-module */

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { waitForDataSourcesLoaded } from "@spreadsheet/../tests/utils/model";

const { toCartesian, toZone } = spreadsheet.helpers;

/**
 * @typedef {import("@spreadsheet/global_filters/plugins/global_filters_core_plugin").GlobalFilter} GlobalFilter
 */

/**
 * Select a cell
 */
export function selectCell(model, xc) {
    const { col, row } = toCartesian(xc);
    return model.selection.selectCell(col, row);
}

/**
 * Add a global filter and ensure the data sources are completely reloaded
 * @param {Model} model
 * @param {{filter: GlobalFilter}} filter
 */
export async function addGlobalFilter(model, filter, fieldMatchings = {}) {
    const result = model.dispatch("ADD_GLOBAL_FILTER", { ...filter, ...fieldMatchings });
    await waitForDataSourcesLoaded(model);
    return result;
}

/**
 * Remove a global filter and ensure the data sources are completely reloaded
 */
export async function removeGlobalFilter(model, id) {
    const result = model.dispatch("REMOVE_GLOBAL_FILTER", { id });
    await waitForDataSourcesLoaded(model);
    return result;
}

/**
 * Edit a global filter and ensure the data sources are completely reloaded
 */
export async function editGlobalFilter(model, filter) {
    const result = model.dispatch("EDIT_GLOBAL_FILTER", filter);
    await waitForDataSourcesLoaded(model);
    return result;
}

/**
 * Set the value of a global filter and ensure the data sources are completely
 * reloaded
 */
export async function setGlobalFilterValue(model, payload) {
    const result = model.dispatch("SET_GLOBAL_FILTER_VALUE", payload);
    await waitForDataSourcesLoaded(model);
    return result;
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

/** Create a test chart in the active sheet*/
export function createBasicChart(model, chartId, sheetId = model.getters.getActiveSheetId()) {
    model.dispatch("CREATE_CHART", {
        id: chartId,
        position: { x: 0, y: 0 },
        sheetId: sheetId,
        definition: {
            title: "test",
            dataSets: ["A1"],
            type: "bar",
            background: "#fff",
            verticalAxisPosition: "left",
            legendPosition: "top",
            stackedBar: false,
        },
    });
}

/** Create a test scorecard chart in the active sheet*/
export function createScorecardChart(model, chartId, sheetId = model.getters.getActiveSheetId()) {
    model.dispatch("CREATE_CHART", {
        id: chartId,
        position: { x: 0, y: 0 },
        sheetId: sheetId,
        definition: {
            title: "test",
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
export function createGaugeChart(model, chartId, sheetId = model.getters.getActiveSheetId()) {
    model.dispatch("CREATE_CHART", {
        id: chartId,
        position: { x: 0, y: 0 },
        sheetId: sheetId,
        definition: {
            title: "test",
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
