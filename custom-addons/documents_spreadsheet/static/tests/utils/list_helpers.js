/** @odoo-module */

import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import {
    patchWithCleanup,
    click,
    getFixture,
    makeDeferred,
    triggerEvent,
    mouseEnter,
    nextTick,
} from "@web/../tests/helpers/utils";
import { findItem } from "@web/../tests/search/helpers";
import { getBasicServerData } from "@spreadsheet/../tests/utils/data";
import {
    getSpreadsheetActionEnv,
    getSpreadsheetActionModel,
    prepareWebClientForSpreadsheet,
} from "@spreadsheet_edition/../tests/utils/webclient_helpers";
import { SpreadsheetAction } from "../../src/bundle/actions/spreadsheet_action";
import { waitForDataSourcesLoaded } from "@spreadsheet/../tests/utils/model";
import { registry } from "@web/core/registry";
import { fieldService } from "@web/core/field_service";
import { contains } from "@web/../tests/utils";
import { onMounted } from "@odoo/owl";

/** @typedef {import("@spreadsheet/o_spreadsheet/o_spreadsheet").Model} Model */

/**
 * Get a webclient with a list view.
 * The webclient is already configured to work with spreadsheet (env, registries, ...)
 *
 * @param {Object} params
 * @param {string} [params.model] Model name of the list
 * @param {Object} [params.serverData] Data to be injected in the mock server
 * @param {Function} [params.mockRPC] Mock rpc function
 * @param {object} [params.additionalContext] additional action context
 * @param {object[]} [params.orderBy] orderBy argument
 * @returns {Promise<object>} Webclient
 */
export async function spawnListViewForSpreadsheet(params = {}) {
    const { model, serverData, mockRPC } = params;
    await prepareWebClientForSpreadsheet();
    const webClient = await createWebClient({
        serverData: serverData || getBasicServerData(),
        mockRPC,
    });

    await doAction(
        webClient,
        {
            name: "Partners",
            res_model: model || "partner",
            type: "ir.actions.act_window",
            views: [[false, "list"]],
            context: {
                group_by: params.groupBy || [],
            },
        },
        { additionalContext: params.additionalContext || {} }
    );

    /** sort the view by field */
    const target = getFixture();
    for (const order of params.orderBy || []) {
        const selector = `thead th.o_column_sortable[data-name='${order.name}']`;
        await click(target.querySelector(selector));
        if (order.asc === false) {
            await click(target.querySelector(selector));
        }
    }
    return webClient;
}

/**
 * Create a spreadsheet model from a List controller
 *
 * @param {object} params
 * @param {string} [params.model] Model name of the list
 * @param {object} [params.serverData] Data to be injected in the mock server
 * @param {function} [params.mockRPC] Mock rpc function
 * @param {object[]} [params.orderBy] orderBy argument
 * @param {(fixture: HTMLElement) => Promise<void>} [params.actions] orderBy argument
 * @param {object} [params.additionalContext] additional action context
 * @param {number} [params.linesNumber]
 *
 * @returns {Promise<{model: Model, webClient: object, env: object}>}
 */
export async function createSpreadsheetFromListView(params = {}) {
    const def = makeDeferred();
    let spreadsheetAction = {};
    patchWithCleanup(SpreadsheetAction.prototype, {
        setup() {
            super.setup();
            onMounted(() => {
                spreadsheetAction = this;
                def.resolve();
            });
        },
    });
    registry.category("services").add("field", fieldService, { force: true });
    const webClient = await spawnListViewForSpreadsheet({
        model: params.model,
        serverData: params.serverData,
        mockRPC: params.mockRPC,
        orderBy: params.orderBy,
        additionalContext: params.additionalContext,
    });
    const target = getFixture();
    if (params.actions) {
        await params.actions(target);
    }
    /** Put the current list in a new spreadsheet */
    await invokeInsertListInSpreadsheetDialog(webClient.env);
    /** @type {HTMLInputElement} */
    const input = target.querySelector(`.o-sp-dialog-meta-threshold-input`);
    input.value = params.linesNumber ? params.linesNumber.toString() : "10";
    await triggerEvent(input, null, "input");
    await click(document.querySelector(".modal-content > .modal-footer > .btn-primary"));
    await def;
    const model = getSpreadsheetActionModel(spreadsheetAction);
    await waitForDataSourcesLoaded(model);
    return {
        webClient,
        model,
        env: getSpreadsheetActionEnv(spreadsheetAction),
    };
}

/**
 * Toggle the CogMenu's Spreadsheet sub-dropdown
 *
 * @param {EventTarget} el
 * @returns Promise
 */
export async function toggleCogMenuSpreadsheet(el) {
    await contains(".o_cp_action_menus .dropdown-toggle", { text: "Spreadsheet" });
    await mouseEnter(findItem(el, ".o_cp_action_menus .dropdown-toggle", "Spreadsheet"));
    await contains(".o-dropdown .show", { text: "Spreadsheet" });
}

/** While the actual flow requires to toggle the list view action menu
 * The current helper uses `contains` which slowsdown drastically the tests
 * This helper takes a shortcut by relying on the implementation
 */
export async function invokeInsertListInSpreadsheetDialog(env) {
    env.bus.trigger("insert-list-spreadsheet");
    await nextTick();
}
