/** @odoo-module */

import { PivotArchParser } from "@web/views/pivot/pivot_arch_parser";
import { nextTick } from "@web/../tests/helpers/utils";

import { OdooPivot } from "@spreadsheet/pivot/pivot_data_source";
import { getBasicServerData, getBasicPivotArch } from "./data";
import { createModelWithDataSource, waitForDataSourcesLoaded } from "./model";

/** @typedef {import("@spreadsheet/o_spreadsheet/o_spreadsheet").Model} Model */

/**
 * @param {Model} model
 * @param {string} pivotId
 * @param {object} params
 * @param {string} params.arch
 * @param {[number, number]} [params.anchor]
 */
export async function insertPivotInSpreadsheet(model, pivotId, params) {
    const archInfo = new PivotArchParser().parse(params.arch || getBasicPivotArch());
    const pivot = {
        type: "ODOO",
        sortedColumn: null,
        domain: [],
        context: {},
        measures: archInfo.activeMeasures,
        model: params.resModel || "partner",
        colGroupBys: archInfo.colGroupBys,
        rowGroupBys: archInfo.rowGroupBys,
        name: "Partner Pivot",
    };
    model.dispatch("ADD_PIVOT", {
        pivotId,
        pivot,
    });
    const ds = model.getters.getPivot(pivotId);
    if (!(ds instanceof OdooPivot)) {
        throw new Error("The pivot data source is not an OdooPivot");
    }
    await ds.load();
    const { cols, rows, measures, rowTitle } = ds.getTableStructure().export();
    const table = {
        cols,
        rows,
        measures,
        rowTitle,
    };
    const [col, row] = params.anchor || [0, 0];
    model.dispatch("INSERT_PIVOT", {
        pivotId,
        sheetId: params.sheetId || model.getters.getActiveSheetId(),
        col,
        row,
        table,
    });
    await nextTick();
}

/**
 * @param {object} params
 * @param {string} [params.arch]
 * @param {object} [params.serverData]
 * @param {function} [params.mockRPC]
 * @returns {Promise<{ model: Model, env: object}>}
 */
export async function createSpreadsheetWithPivot(params = {}) {
    const serverData = params.serverData || getBasicServerData();
    const model = await createModelWithDataSource({
        mockRPC: params.mockRPC,
        serverData: params.serverData,
    });
    const arch = params.arch || serverData.views["partner,false,pivot"];
    const pivotId = "PIVOT#1";
    await insertPivotInSpreadsheet(model, pivotId, { arch });
    const env = model.config.custom.env;
    env.model = model;
    await waitForDataSourcesLoaded(model);
    return { model, env, pivotId };
}
