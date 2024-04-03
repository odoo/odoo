/** @odoo-module */

import { nextTick } from "@web/../tests/helpers/utils";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { createModelWithDataSource } from "./model";
const uuidGenerator = new spreadsheet.helpers.UuidGenerator();

/** @typedef {import("@spreadsheet/o_spreadsheet/o_spreadsheet").Model} Model */

/**
 *
 * @param {Model} model
 */
export function insertChartInSpreadsheet(model, type = "odoo_bar") {
    const definition = getChartDefinition(type);
    model.dispatch("CREATE_CHART", {
        sheetId: model.getters.getActiveSheetId(),
        id: definition.id,
        position: {
            x: 10,
            y: 10,
        },
        definition,
    });
}
/**
 *
 * @param {Object} params
 * @param {function} [params.mockRPC]
 * @param {string} [params.type]
 *
 * @returns { Promise<{ model: Model, env: Object }>}
 */
export async function createSpreadsheetWithChart(params = {}) {
    const model = await createModelWithDataSource({
        mockRPC: params.mockRPC,
    });

    insertChartInSpreadsheet(model, params.type);

    const env = model.config.evalContext.env;
    env.model = model;
    await nextTick();
    return { model, env };
}

function getChartDefinition(type) {
    return {
        metaData: {
            groupBy: ["foo", "bar"],
            measure: "__count",
            order: null,
            resModel: "partner",
        },
        searchParams: {
            comparison: null,
            context: {},
            domain: [],
            groupBy: [],
            orderBy: [],
        },
        stacked: true,
        title: "Partners",
        background: "#FFFFFF",
        legendPosition: "top",
        verticalAxisPosition: "left",
        dataSourceId: uuidGenerator.uuidv4(),
        id: uuidGenerator.uuidv4(),
        type,
    };
}
