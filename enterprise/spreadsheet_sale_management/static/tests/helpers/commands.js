import { helpers } from "@odoo/o-spreadsheet";

import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";
import { getSaleOrderSpreadsheetData } from "./data";

const { toCartesian, toZone } = helpers;

export async function createSaleOrderSpreadsheetModel() {
    const data = getSaleOrderSpreadsheetData();
    return createModelWithDataSource({
        spreadsheetData: data,
    });
}

/**
 * @param {import("@odoo/o-spreadsheet").Model} model
 * @param {string} xc
 * @param {string} fieldName
 * @param {number} indexInList
 * @param {string} sheetId
 */
export function addFieldSync(
    model,
    xc,
    fieldName,
    indexInList,
    sheetId = model.getters.getActiveSheetId()
) {
    return model.dispatch("ADD_FIELD_SYNC", {
        sheetId,
        ...toCartesian(xc),
        listId: model.getters.getMainSaleOrderLineList().id,
        indexInList,
        fieldName,
    });
}

export function deleteFieldSyncs(model, xc, sheetId = model.getters.getActiveSheetId()) {
    return model.dispatch("DELETE_FIELD_SYNCS", { sheetId, zone: toZone(xc) });
}
