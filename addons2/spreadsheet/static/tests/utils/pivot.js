/** @odoo-module */

import { PivotArchParser } from "@web/views/pivot/pivot_arch_parser";
import { nextTick } from "@web/../tests/helpers/utils";

import { PivotDataSource } from "@spreadsheet/pivot/pivot_data_source";
import { getBasicServerData } from "./data";
import { createModelWithDataSource, waitForDataSourcesLoaded } from "./model";

/** @typedef {import("@spreadsheet/o_spreadsheet/o_spreadsheet").Model} Model */

/**
 * @param {Model} model
 * @param {object} params
 * @param {string} params.arch
 * @param {[number, number]} [params.anchor]
 */
export async function insertPivotInSpreadsheet(model, params) {
    const archInfo = new PivotArchParser().parse(params.arch);
    const definition = {
        metaData: {
            colGroupBys: archInfo.colGroupBys,
            rowGroupBys: archInfo.rowGroupBys,
            activeMeasures: archInfo.activeMeasures,
            resModel: params.resModel || "partner",
        },
        searchParams: {
            domain: [],
            context: {},
            groupBy: [],
            orderBy: [],
        },
        name: "Partner Pivot",
    };
    const pivotId = model.getters.getNextPivotId();
    const dataSourceId = model.getters.getPivotDataSourceId(pivotId);
    const dataSource = model.config.custom.dataSources.add(
        dataSourceId,
        PivotDataSource,
        definition
    );
    await dataSource.load();
    const { cols, rows, measures, rowTitle } = dataSource.getTableStructure().export();
    const table = {
        cols,
        rows,
        measures,
        rowTitle,
    };
    const [col, row] = params.anchor || [0, 0];
    model.dispatch("INSERT_PIVOT", {
        id: model.getters.getNextPivotId(),
        sheetId: model.getters.getActiveSheetId(),
        col,
        row,
        table,
        definition,
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
    await insertPivotInSpreadsheet(model, { arch });
    const env = model.config.custom.env;
    env.model = model;
    await waitForDataSourcesLoaded(model);
    return { model, env };
}
