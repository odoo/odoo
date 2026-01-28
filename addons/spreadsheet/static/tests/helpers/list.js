import { waitForDataLoaded } from "@spreadsheet/helpers/model";
import { generateListDefinition } from "@spreadsheet/../tests/helpers/data";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";

/**
 * @typedef {import("@spreadsheet").OdooSpreadsheetModel} OdooSpreadsheetModel
 * @typedef {import("@spreadsheet/o_spreadsheet/o_spreadsheet").Model} Model
 */

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
 * @param {{name: string, asc: boolean}[]} [params.orderBy]
 * @param { "static" | "dynamic"} [mode]
 */
export function insertListInSpreadsheet(model, params, mode = "static") {
    const definition = generateListDefinition(
        params.model,
        params.columns,
        params.actionXmlId,
        params.orderBy
    );
    const listId = model.getters.getNextListId();
    const [col, row] = params.position || [0, 0];

    model.dispatch("INSERT_ODOO_LIST", {
        sheetId: params.sheetId || model.getters.getActiveSheetId(),
        listId,
        linesNumber: params.linesNumber || 10,
        col,
        row,
        definition,
        mode,
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
 * @param {object} [params.modelConfig]
 * @param {{name: string, asc: boolean}[]} [params.orderBy]
 * @param { "static" | "dynamic"} [params.mode]
 *
 * @returns { Promise<{ model: OdooSpreadsheetModel, env: Object }>}
 */
export async function createSpreadsheetWithList(params = {}) {
    const { model, env } = await createModelWithDataSource({
        mockRPC: params.mockRPC,
        serverData: params.serverData,
        modelConfig: params.modelConfig,
    });

    insertListInSpreadsheet(
        model,
        {
            columns: params.columns || [
                { name: "foo", string: "Foo" },
                { name: "bar", string: "Bar" },
                { name: "date", string: "Date" },
                { name: "product_id", string: "Product" },
            ],
            model: params.model || "partner",
            linesNumber: params.linesNumber,
            position: params.position,
            sheetId: params.sheetId,
            orderBy: params.orderBy,
        },
        params.mode
    );

    await waitForDataLoaded(model);
    return { model, env };
}
