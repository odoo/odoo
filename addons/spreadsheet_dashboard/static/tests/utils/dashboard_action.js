/** @odoo-module */

import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { getDashboardServerData } from "./data";

/**
 * @param {object} params
 * @param {object} [params.serverData]
 * @param {function} [params.mockRPC]
 * @param {number} [params.spreadsheetId]
 * @returns {Promise}
 */
export async function createSpreadsheetDashboard(params = {}) {
    const webClient = await createWebClient({
        serverData: params.serverData || getDashboardServerData(),
        mockRPC: params.mockRPC,
    });
    return await doAction(webClient, {
        type: "ir.actions.client",
        tag: "action_spreadsheet_dashboard",
        params: {
            dashboard_id: params.spreadsheetId,
        },
    });
}
