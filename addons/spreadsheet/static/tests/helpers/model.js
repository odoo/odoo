import { after } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Model, owlPlugins, stores } from "@odoo/o-spreadsheet";
import { OdooDataProvider } from "@spreadsheet/data_sources/odoo_data_provider";
import {
    defineActions,
    defineMenus,
    getMockEnv,
    getTestApp,
    makeTestApp,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { setCellContent } from "./commands";
import { addRecordsFromServerData, addViewsFromServerData } from "./data";
import { markRaw } from "@odoo/owl";
import { makeOwlPluginManager } from "./owl_plugins";

const { ModelStore, globalStores, proxifyStoreMutation, DependencyContainer } = stores;
const { ModelPlugin } = owlPlugins;

/**
 * @typedef {import("@spreadsheet/../tests/helpers/data").ServerData} ServerData
 * @typedef {import("@spreadsheet/helpers/model").OdooSpreadsheetModel} OdooSpreadsheetModel
 */

export function setupDataSourceEvaluation(model) {
    model.config.custom.odooDataProvider.addEventListener("data-source-updated", () => {
        const sheetId = model.getters.getActiveSheetId();
        model.dispatch("EVALUATE_CELLS", { sheetId });
    });
}

/**
 * @param {object} params
 * @param {boolean} [params.createMockApp]
 * @param {Array} [params.providedPlugins] owl plugins to provide
 * @param {Array} [params.owlPluginsConfig] config of the owl plugins
 */
export function makeSpreadsheetActionTestEnv(model, params) {
    let container = undefined;
    let getPlugin = undefined;
    if (params.createMockApp) {
        ({ getPlugin, container } = makeOwlPluginManager(params.providedPlugins || [], {
            model,
            ...params.owlPluginsConfig,
        }));
    } else {
        container = new DependencyContainer();
        container.inject(ModelStore, model);
    }

    after(() => {
        container.dispose();
    });

    if (params.createMockApp) {
        // stores use owl plugins in their constructor, which requires the owl scope of the mock app
        for (const store of globalStores.getAll()) {
            container.get(store);
        }
    }
    return {
        model: getPlugin ? getPlugin(ModelPlugin).model : undefined,
        getStore(Store) {
            const store = container.get(Store);
            return proxifyStoreMutation(store, () => container.trigger("store-updated"));
        },
        __spreadsheet_stores__: container,
        getPlugin,
    };
}

/**
 * Create a spreadsheet model with a mocked server environnement
 *
 * @param {object} params
 * @param {object} [params.spreadsheetData] Spreadsheet data to import
 * @param {object} [params.modelConfig]
 * @param {ServerData} [params.serverData] Data to be injected in the mock server
 * @param {function} [params.mockRPC] Mock rpc function
 * @param {boolean} [params.createMockApp]
 * @param {Array} [params.providedPlugins] owl plugins to provide
 * @param {Array} [params.owlPluginsConfig] config of the owl plugins
 * @returns {Promise<{ model: OdooSpreadsheetModel, env: Object }>}
 */
export async function createModelWithDataSource(params = {}) {
    await makeSpreadsheetMockEnv(params);
    const env = getMockEnv();
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
    markRaw(model);
    Object.assign(
        env,
        makeSpreadsheetActionTestEnv(model, {
            createMockApp: params.createMockApp ?? true,
            providedPlugins: params.providedPlugins,
            owlPluginsConfig: params.owlPluginsConfig,
        })
    );

    setupDataSourceEvaluation(model);
    await animationFrame(); // initial async formulas loading
    return { model, env, getPlugin: env.getPlugin };
}

/**
 * Create a mocked server environnement
 *
 * @param {object} params
 * @param {object} [params.spreadsheetData] Spreadsheet data to import
 * @param {ServerData} [params.serverData] Data to be injected in the mock server
 * @param {function} [params.mockRPC] Mock rpc function
 * @returns {Promise<void>}
 */
export async function makeSpreadsheetMockEnv(params = {}) {
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
        addRecordsFromServerData(params.serverData);
    }
    if (params.serverData?.views) {
        addViewsFromServerData(params.serverData);
    }
    if (!getTestApp()) {
        await makeTestApp();
    }
    patchWithCleanup(stores.GridRenderer.prototype, {
        getBoxesWithAnimations(boxes) {
            // disable animations for tests, as they won't work with hoot patched `requestAnimationFrame`
            return boxes;
        },
    });
}

export function createModelFromGrid(grid) {
    const model = new Model();
    for (const xc in grid) {
        if (grid[xc] !== undefined) {
            setCellContent(model, xc, grid[xc]);
        }
    }
    return model;
}
