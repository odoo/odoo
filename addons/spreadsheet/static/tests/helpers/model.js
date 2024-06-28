import { Model } from "@odoo/o-spreadsheet";
import { OdooDataProvider } from "@spreadsheet/data_sources/odoo_data_provider";
import { animationFrame } from "@odoo/hoot-mock";
import { defineActions, defineParams, makeMockEnv, onRpc } from "@web/../tests/web_test_helpers";
import { addRecordsFromServerData, addViewsFromServerData } from "./data";
import { getMockEnv } from "@web/../tests/_framework/env_test_helpers";

/**
 * @typedef {import("@spreadsheet/../tests/helpers/data").ServerData} ServerData
 * @typedef {import("@spreadsheet/helpers/model").OdooSpreadsheetModel} OdooSpreadsheetModel
 * @typedef {import("@web/../tests/_framework/mock_server/mock_server").MockServerEnvironment} MockServerEnvironment
 */

export function setupDataSourceEvaluation(model) {
    model.config.custom.odooDataProvider.addEventListener("data-source-updated", () => {
        const sheetId = model.getters.getActiveSheetId();
        model.dispatch("EVALUATE_CELLS", { sheetId });
    });
}

/**
 * Create a spreadsheet model with a mocked server environnement
 *
 * @param {object} params
 * @param {object} [params.spreadsheetData] Spreadsheet data to import
 * @param {object} [params.modelConfig]
 * @param {ServerData} [params.serverData] Data to be injected in the mock server
 * @param {function} [params.mockRPC] Mock rpc function
 * @returns {Promise<OdooSpreadsheetModel>}
 */
export async function createModelWithDataSource(params = {}) {
    const env = await makeSpreadsheetMockEnv(params);
    const config = params.modelConfig;
    /** @type any*/
    const model = new Model(params.spreadsheetData, {
        ...config,
        custom: {
            env,
            odooDataProvider: new OdooDataProvider(env),
            ...config?.custom,
        },
    });
    // if (params.serverData) {
    //     await addRecordsFromServerData(params.serverData);
    // }
    setupDataSourceEvaluation(model);
    await animationFrame(); // initial async formulas loading
    return model;
}

/**
 * Create a mocked server environnement
 *
 * @param {object} params
 * @param {object} [params.spreadsheetData] Spreadsheet data to import
 * @param {ServerData} [params.serverData] Data to be injected in the mock server
 * @param {function} [params.mockRPC] Mock rpc function
 * @returns {Promise<Object>}
 */
export async function makeSpreadsheetMockEnv(params = {}) {
    if (params.mockRPC) {
        // Note: calling onRpc with only a callback only works for routes such as orm routes that have a default listener
        // For arbitrary rpc request (eg. /web/domain/validate) we need to call onRpc("/my/route", callback)
        onRpc((args) => params.mockRPC(args.route, args)); // separate route from args for legacy (& forward ports) compatibility
    }
    if (params.serverData?.menus) {
        const menus = Object.values(params.serverData.menus);
        defineParams({ menus }, "replace");
    }
    if (params.serverData?.actions) {
        defineActions(Object.values(params.serverData.actions));
    }
    if (params.serverData?.models) {
        addRecordsFromServerData(params.serverData);
    }
    if (params.serverData?.views) {
        addViewsFromServerData(params.serverData);
    }
    const env = getMockEnv() || (await makeMockEnv());
    return env;
}
