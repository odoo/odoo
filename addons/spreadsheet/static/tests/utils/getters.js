/** @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";

const { toCartesian } = spreadsheet.helpers;

/**
 * Get the value of the given cell
 */
export function getCellValue(model, xc, sheetId = model.getters.getActiveSheetId()) {
    const { col, row } = toCartesian(xc);
    const cell = model.getters.getEvaluatedCell({ sheetId, col, row });
    return cell.value;
}

/**
 * Get the cell of the given xc
 */
export function getCell(model, xc, sheetId = model.getters.getActiveSheetId()) {
    const { col, row } = toCartesian(xc);
    return model.getters.getCell({ sheetId, col, row });
}

export function getEvaluatedCell(model, xc, sheetId = model.getters.getActiveSheetId()) {
    const { col, row } = toCartesian(xc);
    return model.getters.getEvaluatedCell({ sheetId, col, row });
}

/**
 * Get the cells of the given sheet (or active sheet if not provided)
 */
export function getCells(model, sheetId = model.getters.getActiveSheetId()) {
    return model.getters.getCells(sheetId);
}

/**
 * Get the formula of the given xc
 */
export function getCellFormula(model, xc, sheetId = model.getters.getActiveSheetId()) {
    const cell = getCell(model, xc, sheetId);
    return cell && cell.isFormula ? model.getters.getFormulaCellContent(sheetId, cell) : "";
}

/**
 * Get the content of the given xc
 */
export function getCellContent(model, xc, sheetId = model.getters.getActiveSheetId()) {
    const { col, row } = toCartesian(xc);
    return model.getters.getCellText({ sheetId, col, row }, true);
}

/**
 * Get the list of the merges (["A1:A2"]) of the sheet
 */
export function getMerges(model, sheetId = model.getters.getActiveSheetId()) {
    return model.exportData().sheets.find((sheet) => sheet.id === sheetId).merges;
}

/**
 * Get the borders at the given XC
 */
export function getBorders(model, xc, sheetId = model.getters.getActiveSheetId()) {
    const { col, row } = toCartesian(xc);
    const borders = model.getters.getCellBorder({ sheetId, col, row });
    if (!borders) {
        return null;
    }
    Object.keys(borders).forEach((key) => borders[key] === undefined && delete borders[key]);
    return borders;
}
