/** @odoo-module **/
import { patchWithCleanup, makeDeferred, nextTick } from "@web/../tests/helpers/utils";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";

import {
    prepareWebClientForSpreadsheet,
    getSpreadsheetActionModel,
    getSpreadsheetActionEnv,
} from "@spreadsheet_edition/../tests/utils/webclient_helpers";
import { DashboardEditAction } from "../../src/bundle/action/dashboard_edit_action";
import { getDashboardBasicServerData } from "./test_data";
import { onMounted } from "@odoo/owl";

/**
 * @typedef {import("@spreadsheet/../tests/utils/data").ServerData} ServerData

 * @typedef {object} SpreadsheetTestParams
 * @property {number} [spreadsheetId]
 * @property {ServerData} [serverData] Data to be injected in the mock server
 * @property {Function} [mockRPC] Mock rpc function
 */

/**
 * @param {SpreadsheetTestParams} params
 */
export async function createDashboardEditAction(params) {
    /** @type {any} */
    let spreadsheetAction;
    const actionMountedDef = makeDeferred();
    patchWithCleanup(DashboardEditAction.prototype, {
        setup() {
            super.setup();
            onMounted(() => actionMountedDef.resolve());
            spreadsheetAction = this;
        },
    });
    await prepareWebClientForSpreadsheet();
    const serverData = params.serverData || getDashboardBasicServerData();
    const webClient = await createWebClient({
        serverData,
        mockRPC: params.mockRPC,
    });
    let spreadsheetId = params.spreadsheetId;
    if (!spreadsheetId) {
        spreadsheetId = createNewDashboard(serverData);
    }
    await doAction(
        webClient,
        {
            type: "ir.actions.client",
            tag: "action_edit_dashboard",
            params: {
                spreadsheet_id: spreadsheetId,
            },
        },
        { clearBreadcrumbs: true } // Sometimes in test defining custom action, Odoo opens on the action instead of opening on root
    );
    await actionMountedDef;
    await nextTick();
    return {
        model: getSpreadsheetActionModel(spreadsheetAction),
        env: getSpreadsheetActionEnv(spreadsheetAction),
    };
}

/**
 *
 * @param {ServerData} serverData
 * @param {object} [data] spreadsheet data
 * @returns {number}
 */
export function createNewDashboard(serverData, data) {
    const dashboards = serverData.models["spreadsheet.dashboard"].records;
    const maxId = dashboards.length ? Math.max(...dashboards.map((d) => d.id)) : 0;
    const spreadsheetId = maxId + 1;
    dashboards.push({
        id: spreadsheetId,
        name: "Untitled Dashboard",
        spreadsheet_data: data ? JSON.stringify(data) : "{}",
    });
    return spreadsheetId;
}
