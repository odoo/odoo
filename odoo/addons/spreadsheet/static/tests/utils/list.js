/** @odoo-module */

import { generateListDefinition } from "./data";
import { createModelWithDataSource, waitForDataSourcesLoaded } from "./model";

/**
 * Insert a list in a spreadsheet model.
 *
 * @param {Model} model
 * @param {Object} params
 * @param {string} params.model
 * @param {Array<string>} params.columns
 * @param {number} [params.linesNumber]
 * @param {[number, number]} [params.position]
 * @param {string} [params.sheetId]
 */
export function insertListInSpreadsheet(model, params) {
    const { definition, columns } = generateListDefinition(params.model, params.columns);
    const [col, row] = params.position || [0, 0];

    model.dispatch("INSERT_ODOO_LIST", {
        sheetId: params.sheetId || model.getters.getActiveSheetId(),
        definition,
        linesNumber: params.linesNumber || 10,
        columns,
        id: model.getters.getNextListId(),
        col,
        row,
    });
}

/**
 *
 * @param {Object} params
 * @param {string} [params.model]
 * @param {Array<string>} [params.columns]
 * @param {Object} [params.serverData]
 * @param {function} [params.mockRPC]
 * @param {number} [params.linesNumber]
 * @param {[number, number]} [params.position]
 * @param {string} [params.sheetId]
 *
 * @returns { Promise<{ model: Model, env: Object }>}
 */
export async function createSpreadsheetWithList(params = {}) {
    const model = await createModelWithDataSource({
        mockRPC: params.mockRPC,
        serverData: params.serverData,
    });

    insertListInSpreadsheet(model, {
        columns: params.columns || ["foo", "bar", "date", "product_id"],
        model: params.model || "partner",
        linesNumber: params.linesNumber,
        position: params.position,
        sheetId: params.sheetId,
    });

    const env = model.config.custom.env;
    env.model = model;
    await waitForDataSourcesLoaded(model);
    return { model, env };
}
