/** @odoo-module */

import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import {
    patchWithCleanup,
    click,
    nextTick,
    getFixture,
    makeDeferred,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import { getBasicServerData } from "@spreadsheet/../tests/utils/data";
import { SpreadsheetAction } from "@documents_spreadsheet/bundle/actions/spreadsheet_action";
import {
    getSpreadsheetActionEnv,
    getSpreadsheetActionModel,
    prepareWebClientForSpreadsheet,
} from "@spreadsheet_edition/../tests/utils/webclient_helpers";
import { waitForDataSourcesLoaded } from "@spreadsheet/../tests/utils/model";
import { registry } from "@web/core/registry";
import { fieldService } from "@web/core/field_service";
import { onMounted } from "@odoo/owl";

/** @typedef {import("@spreadsheet/o_spreadsheet/o_spreadsheet").Model} Model */

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
 * @returns {Promise<object>} Webclient
 */
export async function spawnPivotViewForSpreadsheet(params = {}) {
    await prepareWebClientForSpreadsheet();
    const webClient = await createWebClient({
        serverData: params.serverData || getBasicServerData(),
        mockRPC: params.mockRPC,
    });

    await doAction(
        webClient,
        {
            name: "pivot view",
            res_model: params.model || "partner",
            type: "ir.actions.act_window",
            views: [[false, "pivot"]],
            domain: params.domain,
        },
        {
            additionalContext: params.additionalContext || {},
        }
    );
    return webClient;
}

/**
 * @typedef {object} CreatePivotTestParams
 * @property {Array} [domain] Domain of the pivot
 * @property {string} [model] pivot resModel
 * @property {number} [documentId] ID of an existing document
 * @property {function} [actions] Actions to execute on the pivot view
 *                                before inserting in spreadsheet
 */

/**
 * Create a spreadsheet model from a Pivot controller
 *
 * @param {CreatePivotTestParams & import("../spreadsheet_test_utils").SpreadsheetTestParams} params
 * @returns {Promise<object>} Webclient
 */
export async function createSpreadsheetFromPivotView(params = {}) {
    let spreadsheetAction = {};
    const def = makeDeferred();
    patchWithCleanup(SpreadsheetAction.prototype, {
        setup() {
            super.setup();
            spreadsheetAction = this;
            onMounted(() => {
                def.resolve();
            });
        },
    });
    registry.category("services").add("field", fieldService, { force: true });
    const webClient = await spawnPivotViewForSpreadsheet({
        model: params.model,
        serverData: params.serverData,
        mockRPC: params.mockRPC,
        domain: params.domain,
        additionalContext: params.additionalContext || {},
    });
    const target = getFixture();
    if (params.actions) {
        await params.actions(target);
    }
    await click(target.querySelector(".o_pivot_add_spreadsheet"));
    if (params.documentId) {
        await triggerEvent(
            target,
            `.o-sp-dialog-item div[data-id='${params.documentId}']`,
            "focus"
        );
    }
    await click(document.querySelector(".modal-content > .modal-footer > .btn-primary"));
    await def;
    await nextTick();
    const model = getSpreadsheetActionModel(spreadsheetAction);
    await waitForDataSourcesLoaded(model);
    return {
        webClient,
        env: getSpreadsheetActionEnv(spreadsheetAction),
        model,
    };
}
