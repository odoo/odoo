import {
    defineActions,
    defineMenus,
    getMockEnv,
    makeMockEnv,
    onRpc,
    serverState,
} from "@web/../tests/web_test_helpers";
import { getDocumentsModel } from "./data";

/**
 * @typedef {object} ServerData
 * @property {object} [models]
 * @property {object} [menus]
 * @property {object} [actions]
 */

/**
 * Create a mocked server environment
 * Heavily inspired by spreadsheet's makeSpreadsheetMockEnv
 *
 * @param {object} params
 * @param {ServerData} [params.serverData] Data to be injected in the mock server
 * @param {function} [params.mockRPC] Mock rpc function
 * @returns {Promise<Object>}
 */
export async function makeDocumentsMockEnv(params = {}) {
    if (params.mockRPC) {
        // Note: calling onRpc with only a callback only works for routes such as orm routes that have a default listener
        // For arbitrary rpc request (eg. /web/domain/validate) we need to call onRpc("/my/route", callback)
        onRpc((args) => params.mockRPC(args.route, args)); // separate route from args for legacy (& forward ports) compatibility
    }
    if (params.serverData?.menus) {
        defineMenus(Object.values(params.serverData.menus));
    }
    if (params.serverData?.actions) {
        defineActions(Object.values(params.serverData.actions));
    }
    if (params.serverData?.models) {
        const models = params.serverData.models;
        for (const modelName of Object.keys(models)) {
            const records = models[modelName].records;
            if (!records) {
                continue;
            }
            const PyModel = getDocumentsModel(modelName);
            if (!PyModel) {
                throw new Error(`Model ${modelName} not found inside DocumentsModels`);
            }
            PyModel._records = records;
        }
    }
    const env = getMockEnv() || (await makeMockEnv());
    env.services["document.document"].store.odoobot = { userId: serverState.odoobotId };
    return env;
}
