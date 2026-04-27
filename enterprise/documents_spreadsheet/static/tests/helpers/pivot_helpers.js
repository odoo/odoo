import { SpreadsheetAction } from "@documents_spreadsheet/bundle/actions/spreadsheet_action";
import { getFixture } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { onMounted } from "@odoo/owl";
import { getBasicServerData } from "@documents_spreadsheet/../tests/helpers/data";
import {
    ensureDocumentsRequiredRecords,
    makeDocumentsSpreadsheetMockEnv,
} from "@documents_spreadsheet/../tests/helpers/model";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";
import { createSpreadsheetWithPivot as createSpreadsheetWithPivotSpreadsheet } from "@spreadsheet/../tests/helpers/pivot";
import {
    getSpreadsheetActionEnv,
    getSpreadsheetActionModel,
    prepareWebClientForSpreadsheet,
} from "@spreadsheet_edition/../tests/helpers/webclient_helpers";
import {
    contains,
    getService,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { Deferred } from "@web/core/utils/concurrency";
import { WebClient } from "@web/webclient/webclient";

/**
 * @typedef {import("@spreadsheet/o_spreadsheet/o_spreadsheet").Model} Model
 * @typedef {import("@odoo/o-spreadsheet").Zone} Zone
 */

/**
 * Get a webclient with a pivot view.
 * The webclient is already configured to work with spreadsheet (env, registries, ...)
 *
 * @param {object} params
 * @param {string} [params.model] Model name of the pivot
 * @param {object} [params.serverData] Data to be injected in the mock server
 * @param {function} [params.mockRPC] Mock rpc function
 * @param {any[]} [params.domain] Domain of the pivot
 * @param {object} [params.additionalContext] additional context for the action
 * @param {string} [params.actionXmlId] If set, the pivot view will be loaded from this action - will ignore model and domain
 * @returns {Promise<object>} Webclient
 */
export async function spawnPivotViewForSpreadsheet(params = {}) {
    await prepareWebClientForSpreadsheet();
    await makeDocumentsSpreadsheetMockEnv({
        serverData: params.serverData || getBasicServerData(),
        mockRPC: params.mockRPC,
    });
    const webClient = await mountWithCleanup(WebClient);

    await getService("action").doAction(
        params.actionXmlId || {
            name: "pivot view",
            res_model: params.model || "partner",
            type: "ir.actions.act_window",
            views: [[false, "pivot"]],
            domain: params.domain,
        },
        {
            viewType: "pivot",
            additionalContext: params.additionalContext || {},
        }
    );
    return webClient;
}

/**
 * @typedef {object} CreatePivotTestParams
 * @property {Array} [domain] Domain of the pivot
 * @property {string} [model] pivot resModel
 * @property {string} [actionXmlId] xmlId of the action to load the pivot view from - model and domain will be ignored
 * @property {number} [documentId] ID of an existing document
 * @property {object} [additionalContext] additional context for the action
 * @property {function} [actions] Actions to execute on the pivot view
 *                                before inserting in spreadsheet
 */

/**
 * Create a spreadsheet model from a Pivot controller
 *
 * @param {CreatePivotTestParams & import("@documents_spreadsheet/../tests/helpers/spreadsheet_test_utils").SpreadsheetTestParams} params
 * @returns {Promise<object>} Webclient
 */
export async function createSpreadsheetFromPivotView(params = {}) {
    let spreadsheetAction = {};
    const def = new Deferred();
    patchWithCleanup(SpreadsheetAction.prototype, {
        setup() {
            super.setup();
            spreadsheetAction = this;
            onMounted(() => {
                def.resolve();
            });
        },
    });
    const webClient = await spawnPivotViewForSpreadsheet({
        model: params.model,
        serverData: params.serverData,
        mockRPC: params.mockRPC,
        domain: params.domain,
        additionalContext: params.additionalContext || {},
        actionXmlId: params.actionXmlId,
    });
    const target = getFixture();
    if (params.actions) {
        await params.actions(target);
    }
    await contains(".o_pivot_add_spreadsheet").click();
    if (params.documentId) {
        await contains(`.o-spreadsheet-grid div[data-id='${params.documentId}']`).focus();
    }
    await contains(".modal-content > .modal-footer > .btn-primary").click();
    await def;
    await animationFrame();
    const model = getSpreadsheetActionModel(spreadsheetAction);
    const pivotId = model.getters.getPivotIds()[0];
    await waitForDataLoaded(model);
    const env = getSpreadsheetActionEnv(spreadsheetAction);
    return {
        webClient,
        env,
        model,
        pivotId,
    };
}

export const createSpreadsheetWithPivot = (params = {}) => {
    const extendedParams = { ...params };
    extendedParams.serverData = ensureDocumentsRequiredRecords(params.serverData);
    return createSpreadsheetWithPivotSpreadsheet(extendedParams);
};
